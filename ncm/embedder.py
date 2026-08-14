"""Geração de embeddings para o RAG de NCM (Fase 2).

Padrão **Strategy**: ``Embedder`` é um protocolo estável com duas
implementações:
- ``OpenAIEmbedder`` — usa ``langchain_openai.OpenAIEmbeddings`` (requer
  ``OPENAI_API_KEY``; custo por token).
- ``HashEmbedder`` — determinístico e sem custo (n-gramas de caracteres).
  Usado em testes, CI e demo sem chave de API.

``make_embedder`` escolhe a implementação conforme a disponibilidade da chave.
"""

from __future__ import annotations

import logging
import re
import unicodedata
import zlib
from typing import Protocol

logger = logging.getLogger("tradeflow.ncm.embedder")


class Embedder(Protocol):
    """Contrato de um gerador de embeddings."""

    dimension: int

    def embed(self, text: str) -> list[float]:
        """Gera o vetor de um texto."""
        ...

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Gera vetores para vários textos (permite batching)."""
        ...


def _hash_estavel(texto: str) -> int:
    """Hash determinístico (crc32) — o builtin ``hash()`` é salgado por processo."""
    return zlib.crc32(texto.encode("utf-8"))


def _fold(texto: str) -> str:
    """Minúsculas + remove acentos e não-alfanuméricos por token."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", texto.lower()))


# Stopwords PT comuns que só adicionam ruído à similaridade lexical.
_STOPWORDS = frozenset(
    [
        "de",
        "e",
        "para",
        "com",
        "em",
        "o",
        "a",
        "os",
        "as",
        "um",
        "uma",
        "do",
        "da",
        "dos",
        "das",
        "ou",
        "no",
        "na",
        "por",
        "se",
        "que",
        "ao",
        "aos",
        "pelo",
        "pela",
        "este",
        "esta",
        "estes",
        "estas",
        "esse",
        "essa",
    ]
)


class HashEmbedder:
    """Embedding determinístico por tokens + n-gramas (sem custo).

    Dá peso maior a palavras inteiras (produtos compartilham descritores como
    'torno', 'cabo', 'monitor'), complementadas por n-gramas de caracteres
    para tolerância a variações (singular/plural, prefixos). Stopwords são
    ignoradas e a dimensão é alta para reduzir colisões de hash.
    """

    def __init__(self, dimension: int = 2048, ngram: tuple[int, int] = (3, 4)) -> None:
        self.dimension = dimension
        self.ngram = ngram

    def embed(self, text: str) -> list[float]:
        vetor = [0.0] * self.dimension
        tokens = _fold(text).split()
        for token in tokens:
            if token in _STOPWORDS:
                continue
            idx = _hash_estavel(token) % self.dimension
            vetor[idx] += 3.0  # peso maior para a palavra inteira
            for tamanho in range(self.ngram[0], self.ngram[1] + 1):
                for i in range(len(token) - tamanho + 1):
                    grama = token[i : i + tamanho]
                    vidx = _hash_estavel(grama) % self.dimension
                    vetor[vidx] += 1.0
        # Normaliza (evita vetor nulo).
        norma = sum(v * v for v in vetor) ** 0.5
        if norma > 0:
            vetor = [v / norma for v in vetor]
        return vetor

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class OpenAIEmbedder:
    """Embeddings da OpenAI via ``langchain_openai`` (requer API key)."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        from langchain_openai import OpenAIEmbeddings

        self.model = model
        # model=text-embedding-3-small -> 1536 dimensões.
        self.dimension = 1536
        self._client = OpenAIEmbeddings(model=model, api_key=api_key)

    def embed(self, text: str) -> list[float]:
        return list(self._client.embed_query(text))

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        resultado = self._client.embed_documents(texts)
        return [list(v) for v in resultado]


def make_embedder(api_key: str, model: str | None = None) -> Embedder:
    """Retorna OpenAIEmbedder se houver chave, senão HashEmbedder."""
    if api_key:
        logger.info("usando_openai_embedder", extra={"model": model or "text-embedding-3-small"})
        return OpenAIEmbedder(api_key, model or "text-embedding-3-small")
    logger.warning("sem_openai_api_key_usando_hash_embedder")
    return HashEmbedder()
