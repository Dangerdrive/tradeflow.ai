"""Avaliação de qualidade do RAG NCM (Fase 2).

Mede precision@1 e precision@3 no golden dataset (``data/golden/golden_ncm.json``)
usando o classificador com o embedder disponível (OpenAI se houver chave,
senão HashEmbedder determinístico). Meta do plano: NCM correto entre os 3
sugeridos em >= 85%.

Uso:
    uv run python scripts/evaluate_ncm.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Garante que a raiz do projeto está no path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import get_settings  # noqa: E402
from ncm.classifier import NcmClassifier  # noqa: E402
from ncm.embedder import make_embedder  # noqa: E402
from ncm.vector_store import InMemoryVectorStore  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
TABELA = RAIZ / "data" / "tabela_ncm.csv"
GOLDEN = RAIZ / "data" / "golden" / "golden_ncm.json"


def main() -> None:
    """Roda a avaliação e imprime precision@1 e precision@3."""
    settings = get_settings()
    embedder = make_embedder(settings.openai_api_key)
    store = InMemoryVectorStore()

    classificador = NcmClassifier(embedder, store)
    registros = classificador.index_tabela(TABELA)

    anotacoes = json.loads(GOLDEN.read_text(encoding="utf-8"))
    p1 = 0
    p3 = 0
    total = len(anotacoes)
    erros: list[tuple[str, str, list[str]]] = []

    for descricao, ncm_esperado in sorted(anotacoes.items()):
        sugestoes = classificador.suggest_ncm(descricao, k=3)
        ncm_sugeridos = [s.ncm for s in sugestoes]
        if ncm_sugeridos and ncm_sugeridos[0] == ncm_esperado:
            p1 += 1
        if ncm_esperado in ncm_sugeridos:
            p3 += 1
        else:
            erros.append((descricao, ncm_esperado, ncm_sugeridos))

    print(f"Tabela indexada: {registros} registros | Embedder: {type(embedder).__name__}")
    print(f"precision@1: {p1}/{total} ({100.0 * p1 / total:.0f}%)")
    print(f"precision@3: {p3}/{total} ({100.0 * p3 / total:.0f}%)")
    print(f"Meta (precision@3 >= 85%): {'OK' if p3 / total >= 0.85 else 'FALHOU'}")
    for descricao, esperado, obtidos in erros:
        print(f"  ERRO: {descricao!r} esperado={esperado} obtidos={obtidos}")


if __name__ == "__main__":
    main()
