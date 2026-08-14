"""Banco vetorial para o RAG de NCM (Fase 2).

Padrão **Strategy/Repository**: ``VectorStore`` é um protocolo estável com
duas implementações:
- ``ChromaVectorStore`` — persistente, via ChromaDB (produção).
- ``InMemoryVectorStore`` — força bruta por cosseno (testes/demo rápida).

O classificador depende apenas do protocolo — trocar a implementação não
altera o código cliente.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Hit:
    """Um resultado de busca no banco vetorial."""

    document: str
    metadata: dict
    score: float


class VectorStore(Protocol):
    """Contrato de um banco vetorial."""

    def add(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        embeddings: list[list[float]],
    ) -> None: ...

    def query(self, embedding: list[float], n_results: int = 5) -> list[Hit]: ...


class ChromaVectorStore:
    """Implementação persistente com ChromaDB (client local)."""

    def __init__(
        self,
        persist_dir: str,
        collection_name: str = "ncm",
    ) -> None:
        import chromadb

        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        self._collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def query(self, embedding: list[float], n_results: int = 5) -> list[Hit]:
        resultado = self._collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
        )
        hits: list[Hit] = []
        docs = (resultado.get("documents") or [[]])[0]
        metas = (resultado.get("metadatas") or [[]])[0]
        distancias = (resultado.get("distances") or [[]])[0]
        for doc, meta, dist in zip(docs, metas, distancias, strict=True):
            hits.append(Hit(document=doc, metadata=dict(meta or {}), score=1.0 - float(dist)))
        return hits


class InMemoryVectorStore:
    """Implementação em memória (cosseno) — testes e demo sem persistência."""

    def __init__(self) -> None:
        self._ids: list[str] = []
        self._documents: list[str] = []
        self._metadatas: list[dict] = []
        self._embeddings: list[list[float]] = []

    def add(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        self._ids.extend(ids)
        self._documents.extend(documents)
        self._metadatas.extend(metadatas)
        self._embeddings.extend(embeddings)

    def query(self, embedding: list[float], n_results: int = 5) -> list[Hit]:
        escores = [(self._cosseno(embedding, v), i) for i, v in enumerate(self._embeddings)]
        escores.sort(key=lambda t: t[0], reverse=True)
        hits: list[Hit] = []
        for score, i in escores[:n_results]:
            hits.append(Hit(document=self._documents[i], metadata=self._metadatas[i], score=score))
        return hits

    @staticmethod
    def _cosseno(a: list[float], b: list[float]) -> float:
        if len(a) != len(b):
            raise ValueError("dimensões divergentes")
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        na = math.sqrt(sum(x * x for x in a)) or 1.0
        nb = math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (na * nb)


def make_vector_store(persist_dir: str | None = None) -> VectorStore:
    """Retorna ChromaVectorStore (persistente) ou InMemoryVectorStore."""
    if persist_dir:
        return ChromaVectorStore(persist_dir)
    return InMemoryVectorStore()
