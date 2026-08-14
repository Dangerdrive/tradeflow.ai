"""Classificação NCM via RAG (Fase 2).

Carrega a Tabela TIPI (CSV) em um banco vetorial e sugere os k códigos NCM
mais prováveis para uma descrição de produto (similaridade de embedding).

Interface estável:
    classifier = NcmClassifier(embedder, vector_store)
    classifier.index_tabela("data/tabela_ncm.csv")
    sugestoes = classifier.suggest_ncm("Televisor LED 55 polegadas", k=3)
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path

from ncm.embedder import Embedder
from ncm.vector_store import VectorStore

logger = logging.getLogger("tradeflow.ncm.classifier")


@dataclass(frozen=True)
class NcmSuggestion:
    """Uma sugestão de código NCM."""

    ncm: str
    descricao: str
    score: float
    aliquota: float | None = None


class NcmClassifier:
    """Classificador NCM por similaridade (RAG sobre a Tabela TIPI)."""

    def __init__(self, embedder: Embedder, vector_store: VectorStore) -> None:
        self._embedder = embedder
        self._store = vector_store
        self._indexado: bool = False

    # ------------------------------------------------------------------ API

    def index_tabela(self, csv_path: str | Path) -> int:
        """Lê a Tabela NCM (CSV: ncm, descricao, aliquota_ii) e indexa.

        Returns:
            Número de registros indexados.
        """
        linhas = self._ler_csv(csv_path)
        if not linhas:
            raise ValueError(f"Tabela NCM vazia: {csv_path}")

        ids = [linha["ncm"] for linha in linhas]
        documentos = [linha["descricao"] for linha in linhas]
        metadatas = [
            {
                "ncm": linha["ncm"],
                "descricao": linha["descricao"],
                "aliquota_ii": linha["aliquota_ii"],
            }
            for linha in linhas
        ]
        embeddings = self._embedder.embed_many(documentos)

        self._store.add(ids=ids, documents=documentos, metadatas=metadatas, embeddings=embeddings)
        self._indexado = True
        logger.info("tabela_ncm_indexada", extra={"registros": len(linhas)})
        return len(linhas)

    def suggest_ncm(self, descricao: str, k: int = 3) -> list[NcmSuggestion]:
        """Sugere os k NCMs mais prováveis para ``descricao``."""
        if not self._indexado:
            raise RuntimeError("Tabela NCM não indexada — chame index_tabela() antes.")

        embedding = self._embedder.embed(descricao)
        hits = self._store.query(embedding, n_results=k)

        sugestoes: list[NcmSuggestion] = []
        for hit in hits:
            ncm = hit.metadata.get("ncm", "")
            aliquota = hit.metadata.get("aliquota_ii")
            sugestoes.append(
                NcmSuggestion(
                    ncm=ncm,
                    descricao=hit.metadata.get("descricao", hit.document),
                    score=hit.score,
                    aliquota=float(aliquota) if aliquota is not None else None,
                )
            )
        return sugestoes

    # ------------------------------------------------------------- helpers

    @staticmethod
    def _ler_csv(csv_path: str | Path) -> list[dict]:
        """Lê o CSV da Tabela NCM e normaliza os campos."""
        caminho = Path(csv_path)
        with caminho.open(newline="", encoding="utf-8") as arquivo:
            leitor = csv.DictReader(arquivo)
            linhas: list[dict] = []
            for linha in leitor:
                ncm = (linha.get("ncm") or "").strip()
                descricao = (linha.get("descricao") or "").strip()
                if not ncm or not descricao:
                    continue
                try:
                    aliquota = float(linha.get("aliquota_ii") or 0)
                except ValueError:
                    aliquota = 0.0
                linhas.append({"ncm": ncm, "descricao": descricao, "aliquota_ii": aliquota})
            return linhas
