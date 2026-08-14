"""Testes da camada de dados (Fase 4) — SQLite em memória."""

import pytest
from sqlalchemy.exc import IntegrityError

from extraction.schemas import Incoterm, InvoiceData, InvoiceItem
from storage.db import Base, get_engine
from storage.models import STATUS_CONCLUIDO, STATUS_PENDENTE
from storage.repositories import ImportacaoRepository, ItemRepository


@pytest.fixture()
def session():
    """Sessão SQLite em memória com tabelas criadas."""
    engine = get_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    from sqlalchemy.orm import Session

    with Session(engine) as s:
        yield s
    Base.metadata.drop_all(bind=engine)


def test_repo_cria_e_busca_importacao(session) -> None:
    repo = ImportacaoRepository(session)
    imp = repo.create(numero_fatura="INV-1", fornecedor="ACME")
    session.commit()

    obtida = repo.get(imp.id)
    assert obtida is not None
    assert obtida.status == STATUS_PENDENTE
    assert repo.count() == 1


def test_constraint_unica_fatura_fornecedor(session) -> None:
    repo = ImportacaoRepository(session)
    repo.create(numero_fatura="INV-1", fornecedor="ACME")
    session.commit()

    with pytest.raises(IntegrityError):
        repo.create(numero_fatura="INV-1", fornecedor="ACME")
        session.commit()


def test_criar_de_invoice_persiste_itens(session) -> None:
    repo = ImportacaoRepository(session)
    invoice = InvoiceData(
        numero_fatura="INV-2026-1",
        fornecedor="Tech Global",
        valor_total_usd=100.0,
        incoterm=Incoterm.FOB,
        volumes=2,
        itens=[
            InvoiceItem(descricao="TV", quantidade=1, valor=60.0, ncm="8528.72.00"),
            InvoiceItem(descricao="Cabo", quantidade=10, valor=40.0),
        ],
    )
    imp = repo.criar_de_invoice(invoice)
    session.commit()

    assert len(imp.itens) == 2
    assert imp.itens[0].ncm == "8528.72.00"
    assert imp.payload_bruto["numero_fatura"] == "INV-2026-1"


def test_atualiza_status_e_resultados(session) -> None:
    repo = ImportacaoRepository(session)
    imp = repo.create(numero_fatura="INV-2", fornecedor="Beta")
    session.commit()

    repo.atualizar_resultado(
        imp.id,
        ncm_sugerido="8528.72.00",
        prazo_estimado_dias=9,
        status=STATUS_CONCLUIDO,
    )
    session.commit()

    obtida = repo.get(imp.id)
    assert obtida.ncm_sugerido == "8528.72.00"
    assert obtida.prazo_estimado_dias == 9
    assert obtida.status == STATUS_CONCLUIDO


def test_find_by_fatura_para_idempotencia(session) -> None:
    repo = ImportacaoRepository(session)
    repo.create(numero_fatura="INV-3", fornecedor="Gama")
    session.commit()

    assert repo.find_by_fatura("INV-3", "Gama") is not None
    assert repo.find_by_fatura("INV-3", "Outro") is None


def test_list_ordenada_por_data(session) -> None:
    repo = ImportacaoRepository(session)
    a = repo.create(numero_fatura="A", fornecedor="X")
    b = repo.create(numero_fatura="B", fornecedor="X")
    session.commit()

    lista = repo.list()
    assert [i.id for i in lista] == [b.id, a.id]


def test_item_repository(session) -> None:
    repo = ImportacaoRepository(session)
    imp = repo.create(numero_fatura="INV-4", fornecedor="Delta")
    session.commit()

    item_repo = ItemRepository(session)
    item = item_repo.add(imp.id, InvoiceItem(descricao="Parafuso", quantidade=100, valor=5.0))
    session.commit()

    assert item_repo.list_by_importacao(imp.id)[0].descricao == "Parafuso"
    assert item.importacao_id == imp.id


def test_status_invalidos_bloqueados() -> None:
    from storage.models import STATUS_VALIDOS

    assert "pendente" in STATUS_VALIDOS
    assert "revisado" in STATUS_VALIDOS
    assert "nao-existe" not in STATUS_VALIDOS
