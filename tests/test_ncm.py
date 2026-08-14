"""Testes do RAG NCM (Fase 2) — HashEmbedder + InMemoryVectorStore, sem rede."""

import json
from pathlib import Path

from ncm.classifier import NcmClassifier, NcmSuggestion
from ncm.embedder import HashEmbedder, make_embedder
from ncm.vector_store import InMemoryVectorStore

RAIZ = Path(__file__).resolve().parents[1]
TABELA = RAIZ / "data" / "tabela_ncm.csv"
GOLDEN = RAIZ / "data" / "golden" / "golden_ncm.json"


def _classificador():
    embedder = HashEmbedder()
    store = InMemoryVectorStore()
    classificador = NcmClassifier(embedder, store)
    classificador.index_tabela(TABELA)
    return classificador


def test_indexa_tabela() -> None:
    _classificador()
    # A tabela deve ter dezenas de registros (não vazia).
    assert len(TABELA.read_text(encoding="utf-8").splitlines()) > 30


def test_suggest_ncm_retorna_k_sugestoes() -> None:
    classificador = _classificador()
    sugestoes = classificador.suggest_ncm("Televisor LED 55 polegadas", k=3)
    assert len(sugestoes) == 3
    for s in sugestoes:
        assert isinstance(s, NcmSuggestion)
        assert s.ncm and s.descricao


def test_precision_3_no_golden() -> None:
    """Meta do plano: NCM correto entre os 3 sugeridos em >= 85%."""
    classificador = _classificador()
    anotacoes = json.loads(GOLDEN.read_text(encoding="utf-8"))
    acertos = 0
    for descricao, ncm_esperado in anotacoes.items():
        sugestoes = classificador.suggest_ncm(descricao, k=3)
        if ncm_esperado in [s.ncm for s in sugestoes]:
            acertos += 1
    taxa = acertos / len(anotacoes)
    assert taxa >= 0.85, f"precision@3 = {taxa:.2f} (abaixo de 0.85)"


def test_suggest_antes_de_indexar_levanta_erro() -> None:
    embedder = HashEmbedder()
    store = InMemoryVectorStore()
    classificador = NcmClassifier(embedder, store)
    try:
        classificador.suggest_ncm("qualquer coisa")
    except RuntimeError as exc:
        assert "indexada" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("deveria levantar RuntimeError")


def test_make_embedder_sem_chave_usa_hash() -> None:
    embedder = make_embedder("")
    assert isinstance(embedder, HashEmbedder)


def test_make_embedder_com_chave_usa_openai() -> None:
    embedder = make_embedder("sk-placeholder")
    assert type(embedder).__name__ == "OpenAIEmbedder"
