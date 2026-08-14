"""Testes da API REST (Fase 6) — TestClient + SQLite em memória."""

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from config.settings import get_settings
from storage.db import Base, get_engine, get_session_factory, session_scope
from storage.models import STATUS_PENDENTE
from storage.repositories import ImportacaoRepository
from tests.fixtures.sample_pdf import INVOICE_EN, make_pdf


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Client da API com banco SQLite em temp."""
    url = f"sqlite:///{tmp_path / 'api.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    Base.metadata.create_all(bind=get_engine(url))

    app = create_app(get_settings())
    with TestClient(app) as c:
        yield c

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


def _pdf_bytes() -> bytes:
    return make_pdf(INVOICE_EN)


def test_health(client) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_upload_pdf_retorna_202(client, monkeypatch) -> None:
    # Não executa o worker em background no teste.
    monkeypatch.setattr("jobs.worker.enfileirar_processamento", lambda *a, **k: None)

    resp = client.post(
        "/importacoes/upload",
        files={"arquivo": ("fatura.pdf", _pdf_bytes(), "application/pdf")},
    )
    assert resp.status_code == 202
    corpo = resp.json()
    assert corpo["importacao_id"] > 0
    assert corpo["status"] == STATUS_PENDENTE


def test_upload_extensao_invalida_retorna_400(client) -> None:
    resp = client.post(
        "/importacoes/upload",
        files={"arquivo": ("nota.txt", b"conteudo", "text/plain")},
    )
    assert resp.status_code == 400
    assert "Extensão" in resp.json()["detalhe"]


def test_get_importacao_retorna_detalhe(client) -> None:
    with session_scope() as sessao:
        imp = ImportacaoRepository(sessao).create(
            numero_fatura="INV-1", fornecedor="ACME", valor_total_usd=100.0
        )
        imp_id = imp.id

    resp = client.get(f"/importacoes/{imp_id}")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["numero_fatura"] == "INV-1"
    assert corpo["fornecedor"] == "ACME"
    assert "itens" in corpo


def test_get_importacao_inexistente_retorna_404(client) -> None:
    resp = client.get("/importacoes/99999")
    assert resp.status_code == 404


def test_get_status(client) -> None:
    with session_scope() as sessao:
        imp = ImportacaoRepository(sessao).create(numero_fatura="INV-2", fornecedor="Beta")
        imp_id = imp.id

    resp = client.get(f"/importacoes/{imp_id}/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == STATUS_PENDENTE


def test_listar_importacoes(client) -> None:
    with session_scope() as sessao:
        repo = ImportacaoRepository(sessao)
        repo.create(numero_fatura="A", fornecedor="X")
        repo.create(numero_fatura="B", fornecedor="Y")

    resp = client.get("/importacoes")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_api_key_obrigatoria_quando_configurada(tmp_path, monkeypatch) -> None:
    url = f"sqlite:///{tmp_path / 'apikey.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    Base.metadata.create_all(bind=get_engine(url))

    settings = get_settings()
    app = create_app(settings.model_copy(update={"api_key": "segredo"}))
    with TestClient(app) as c:
        # Sem a chave -> 401.
        assert c.get("/importacoes").status_code == 401
        # Com a chave -> 200.
        assert c.get("/importacoes", headers={"X-API-Key": "segredo"}).status_code == 200
        # Chave errada -> 401.
        assert c.get("/importacoes", headers={"X-API-Key": "errada"}).status_code == 401

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
