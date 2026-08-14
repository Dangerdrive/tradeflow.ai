"""Testes do pipeline de orquestração (Fase 5) — componentes fake, sem rede."""

from pathlib import Path

import pytest

from agents.pipeline import PipelineResult, TradeFlowPipeline
from config.settings import get_settings
from extraction.schemas import Incoterm, InvoiceData, InvoiceItem
from ncm.classifier import NcmSuggestion
from storage.db import Base, get_engine, get_session_factory
from storage.models import STATUS_CONCLUIDO, STATUS_ERRO, Importacao
from storage.repositories import ImportacaoRepository


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """Banco SQLite em temp + settings apontando para ele."""
    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    # Limpa caches para o Settings/engine relerem a URL do ambiente.
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    Base.metadata.create_all(bind=get_engine(url))
    yield url
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


class _FakeExtrator:
    def __init__(self, dados: InvoiceData | None = None, falha: bool = False) -> None:
        self.dados = dados
        self.falha = falha

    def extract_from_pdf(self, pdf_path: str | Path, *, ocr: bool = False) -> InvoiceData:
        if self.falha:
            raise RuntimeError("PDF corrompido")
        return self.dados or _invoice()


class _FakeClassificador:
    def __init__(self, sugestao: NcmSuggestion | None = None, falha: bool = False) -> None:
        self.sugestao = sugestao
        self.falha = falha

    def suggest_ncm(self, descricao: str, k: int = 3) -> list[NcmSuggestion]:
        if self.falha:
            raise RuntimeError("índice indisponível")
        if self.sugestao:
            return [self.sugestao]
        return [NcmSuggestion(ncm="8528.72.00", descricao="Televisor", score=0.9, aliquota=20.0)]


class _FakePreditor:
    def predict(self, **kwargs) -> int:
        return 9


def _invoice() -> InvoiceData:
    return InvoiceData(
        numero_fatura="INV-2026-0842",
        fornecedor="Tech Global Ltd.",
        valor_total_usd=12850.40,
        peso_bruto_kg=320.5,
        incoterm=Incoterm.FOB,
        volumes=12,
        itens=[
            InvoiceItem(
                descricao="Televisor LED 55",
                quantidade=10,
                valor=12850.40,
                ncm="8528.72.00",
            )
        ],
    )


class _NaoInformado:
    pass


_NAO = _NaoInformado()


def _pipeline(extrator=_NAO, classificador=_NAO, preditor=_NAO) -> TradeFlowPipeline:
    return TradeFlowPipeline(
        extrator=_FakeExtrator() if extrator is _NAO else extrator,
        classificador=_FakeClassificador() if classificador is _NAO else classificador,
        preditor=_FakePreditor() if preditor is _NAO else preditor,
    )


def test_pipeline_completo_persiste(db, tmp_path) -> None:
    resultado = _pipeline().process_pdf(tmp_path / "fatura.pdf")
    assert isinstance(resultado, PipelineResult)
    assert resultado.status == STATUS_CONCLUIDO
    assert resultado.ncm_sugerido is not None
    assert resultado.prazo_estimado_dias == 9
    assert resultado.importacao_id is not None
    assert "extracao_s" in resultado.metricas

    with get_engine(db).connect() as conn:
        total = conn.execute(Importacao.__table__.select()).fetchall()
    assert len(total) == 1


def test_pipeline_idempotente_nao_duplica(db, tmp_path) -> None:
    pipeline = _pipeline()
    r1 = pipeline.process_pdf(tmp_path / "fatura.pdf")
    r2 = pipeline.process_pdf(tmp_path / "fatura.pdf")
    assert r1.importacao_id == r2.importacao_id

    with get_engine(db).connect() as conn:
        total = conn.execute(Importacao.__table__.select()).fetchall()
    assert len(total) == 1


def test_pipeline_falha_extracao_retorna_erro(db, tmp_path) -> None:
    resultado = _pipeline(extrator=_FakeExtrator(falha=True)).process_pdf(tmp_path / "fatura.pdf")
    assert resultado.status == STATUS_ERRO
    assert "extração" in (resultado.erro or "").lower()


def test_pipeline_falha_ncm_nao_derruba(db, tmp_path) -> None:
    resultado = _pipeline(classificador=_FakeClassificador(falha=True)).process_pdf(
        tmp_path / "fatura.pdf"
    )
    assert resultado.status == STATUS_CONCLUIDO
    assert resultado.ncm_sugerido is None
    assert resultado.prazo_estimado_dias == 9


def test_pipeline_sem_preditor_segue_sem_prazo(db, tmp_path) -> None:
    resultado = _pipeline(preditor=None).process_pdf(tmp_path / "fatura.pdf")
    assert resultado.status == STATUS_CONCLUIDO
    assert resultado.prazo_estimado_dias is None


def test_pipeline_atualiza_registro_existente(db, tmp_path) -> None:
    from storage.db import session_scope

    with session_scope() as sessao:
        repo = ImportacaoRepository(sessao)
        pendente = repo.create(numero_fatura="PENDENTE", fornecedor="?")
        id_pendente = pendente.id

    resultado = _pipeline().process_pdf(tmp_path / "fatura.pdf", importacao_id=id_pendente)
    assert resultado.importacao_id == id_pendente

    with get_engine(db).connect() as conn:
        linhas = conn.execute(Importacao.__table__.select()).fetchall()
    assert len(linhas) == 1
    assert linhas[0][1] == "INV-2026-0842"


def test_pipeline_merge_evita_duplicata_na_idempotencia(db, tmp_path) -> None:
    """Upload de fatura já existente: placeholder é removido e o canônico atualizado."""
    from storage.db import session_scope

    r1 = _pipeline().process_pdf(tmp_path / "fatura.pdf")
    id_canonico = r1.importacao_id

    with session_scope() as sessao:
        repo = ImportacaoRepository(sessao)
        placeholder = repo.create(numero_fatura="UPLOAD-X", fornecedor="?")
        id_placeholder = placeholder.id

    r2 = _pipeline().process_pdf(tmp_path / "fatura.pdf", importacao_id=id_placeholder)

    assert r2.importacao_id == id_canonico

    with get_engine(db).connect() as conn:
        linhas = conn.execute(Importacao.__table__.select()).fetchall()
    assert len(linhas) == 1
    assert linhas[0][0] == id_canonico
