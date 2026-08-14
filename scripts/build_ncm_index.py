"""Constrói/persiste o índice vetorial NCM (Fase 2).

Lê ``data/tabela_ncm.csv`` e indexa no ChromaDB em ``data/chroma/`` usando o
embedder disponível (OpenAI se houver ``OPENAI_API_KEY``, senão HashEmbedder).

Uso:
    uv run python scripts/build_ncm_index.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Garante que a raiz do projeto está no path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import get_settings  # noqa: E402
from ncm.classifier import NcmClassifier  # noqa: E402
from ncm.embedder import make_embedder  # noqa: E402
from ncm.vector_store import ChromaVectorStore  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]


def main() -> None:
    """Indexa a Tabela NCM no ChromaDB persistente."""
    settings = get_settings()
    embedder = make_embedder(settings.openai_api_key)

    store = ChromaVectorStore(persist_dir=settings.chroma_persist_dir)
    classificador = NcmClassifier(embedder, store)
    registros = classificador.index_tabela(RAIZ / "data" / "tabela_ncm.csv")
    print(f"Índice NCM persistido em {settings.chroma_persist_dir} ({registros} registros)")


if __name__ == "__main__":
    main()
