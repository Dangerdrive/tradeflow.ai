"""Teste E2E do fluxo completo (Fase 8) — componentes determinísticos, sem rede.

Exercita o caminho feliz de ponta a ponta com um PDF real gerado:
upload (API) → extração (regex) → NCM (hash embedder) → prazo (modelo treinado)
→ persistência → status consultável.
"""

from pathlib import Path

import pytest

from agents.pipeline import TradeFlowPipeline
from config.settings import get_settings
from extraction.parser import extract_text
from extraction.regex_fallback import extract_fields_regex
from ncm.classifier import NcmClassifier
from ncm.embedder import HashEmbedder
from ncm.vector_store import InMemoryVectorStore
from prediction.model import PrazoPredictor
from prediction.train import treinar
from storage.db import Base, get_engine, get_session_factory, session_scope
from storage.models import STATUS_CONCLUIDO
from storage.repositories import ImportacaoRepository
from tests.fixtures.sample_pdf import INVOICE_EN, make_pdf

RAIZ = Path(__file__).resolve().parents[1]
TABELA_NCM = RAIZ / "data" / "tabela_ncm.csv"
DATASET = RAIZ / "data" / "historico_importacoes.csv"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """Banco SQLite em temp + settings apontando para ele."""
    url = f"sqlite:///{tmp_path / 'e2e.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    Base.metadata.create_all(bind=get_engine(url))
    yield url
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


class _ExtratorRegex:
    """Extrator determinístico (regex sobre o texto do PDF)."""

    def extract_from_pdf(self, pdf_path: str | Path, *, ocr: bool = False):
        from extraction.schemas import InvoiceData

        texto = extract_text(pdf_path, ocr=ocr)
        dados = extract_fields_regex(texto)
        assert isinstance(dados, InvoiceData)
        return dados


def _pipeline_real(tmp_path) -> TradeFlowPipeline:
    """Pipeline com componentes reais (determinísticos, sem LLM)."""
    # Classificador NCM com HashEmbedder + tabela indexada.
    classificador = NcmClassifier(HashEmbedder(), InMemoryVectorStore())
    classificador.index_tabela(TABELA_NCM)

    # Modelo de prazo treinado em temp (determinístico).
    artefato = tmp_path / "prazo.joblib"
    treinar(DATASET, artefato)
    preditor = PrazoPredictor(artefato)

    return TradeFlowPipeline(_ExtratorRegex(), classificador, preditor)


def test_e2e_pipeline_completo_persiste(db, tmp_path) -> None:
    pdf = tmp_path / "fatura.pdf"
    pdf.write_bytes(make_pdf(INVOICE_EN))

    resultado = _pipeline_real(tmp_path).process_pdf(pdf)
    assert resultado.status == STATUS_CONCLUIDO
    assert resultado.invoice.numero_fatura == "INV-2026-0842"
    assert resultado.invoice.fornecedor == "Tech Global Ltd."
    assert resultado.ncm_sugerido is not None
    assert resultado.prazo_estimado_dias is not None
    assert resultado.importacao_id is not None

    # Registro completo no banco (fatura, NCM, prazo e itens).
    with session_scope() as sessao:
        reg = ImportacaoRepository(sessao).get(resultado.importacao_id)
    assert reg is not None
    assert reg.numero_fatura == "INV-2026-0842"
    assert reg.ncm_sugerido == resultado.ncm_sugerido.ncm
    assert reg.prazo_estimado_dias == resultado.prazo_estimado_dias
    assert len(reg.itens) >= 1


def test_e2e_api_upload_status(db, tmp_path, monkeypatch) -> None:
    """Upload via API e status consultável após processamento síncrono."""
    from fastapi.testclient import TestClient

    from api.main import create_app

    pdf_bytes = make_pdf(INVOICE_EN)

    # Impede o worker real; processamos de forma síncrona no teste.
    monkeypatch.setattr("jobs.worker.enfileirar_processamento", lambda *a, **k: None)

    app = create_app(get_settings())
    with TestClient(app) as client:
        resp = client.post(
            "/importacoes/upload",
            files={"arquivo": ("fatura.pdf", pdf_bytes, "application/pdf")},
        )
        assert resp.status_code == 202
        importacao_id = resp.json()["importacao_id"]

        # Processa o PDF salvo (worker simulado) sobre o registro criado.
        from jobs.worker import _processar

        uploads = RAIZ / "data" / "raw" / "uploads"
        pdf_salvo = next(uploads.glob("*.pdf"))
        _processar(pdf_salvo, importacao_id)

        status = client.get(f"/importacoes/{importacao_id}/status")
        assert status.status_code == 200
        assert status.json()["status"] == STATUS_CONCLUIDO

        detalhe = client.get(f"/importacoes/{importacao_id}")
        assert detalhe.status_code == 200
        corpo = detalhe.json()
        assert corpo["numero_fatura"] == "INV-2026-0842"
        assert corpo["ncm_sugerido"] is not None
