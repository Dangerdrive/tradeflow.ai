"""Testes de schema da extração (InvoiceData / InvoiceItem)."""

import pytest
from pydantic import ValidationError

from extraction.schemas import Incoterm, InvoiceData, InvoiceItem


def test_incoterm_valido_aceito() -> None:
    fatura = InvoiceData(
        numero_fatura="INV-1",
        fornecedor="ACME",
        valor_total_usd=100.0,
        incoterm="FOB",
    )
    assert fatura.incoterm == Incoterm.FOB


def test_incoterm_invalido_rejeitado() -> None:
    with pytest.raises(ValidationError):
        InvoiceData(
            numero_fatura="INV-1",
            fornecedor="ACME",
            valor_total_usd=100.0,
            incoterm="XYZ",
        )


def test_ncm_normaliza_formatos() -> None:
    item = InvoiceItem(descricao="TV", quantidade=1, valor=10.0, ncm="85287200")
    assert item.ncm == "8528.72.00"

    item2 = InvoiceItem(descricao="TV", quantidade=1, valor=10.0, ncm="8528.72.00")
    assert item2.ncm == "8528.72.00"


def test_ncm_invalido_rejeitado() -> None:
    with pytest.raises(ValidationError):
        InvoiceItem(descricao="TV", quantidade=1, valor=10.0, ncm="abc")


def test_valor_total_negativo_rejeitado() -> None:
    with pytest.raises(ValidationError):
        InvoiceData(
            numero_fatura="INV-1",
            fornecedor="ACME",
            valor_total_usd=-5.0,
            incoterm="FOB",
        )


def test_soma_itens_nao_pode_exceder_total() -> None:
    with pytest.raises(ValidationError):
        InvoiceData(
            numero_fatura="INV-1",
            fornecedor="ACME",
            valor_total_usd=100.0,
            incoterm="FOB",
            itens=[
                InvoiceItem(descricao="A", quantidade=1, valor=90.0),
                InvoiceItem(descricao="B", quantidade=1, valor=30.0),
            ],
        )


def test_normaliza_espacos_em_texto() -> None:
    fatura = InvoiceData(
        numero_fatura="  INV-1  ",
        fornecedor="  ACME  ",
        valor_total_usd=10.0,
        incoterm="FOB",
    )
    assert fatura.numero_fatura == "INV-1"
    assert fatura.fornecedor == "ACME"


def test_incoterms_suportados() -> None:
    for codigo in ["EXW", "FCA", "FAS", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP"]:
        assert Incoterm(codigo) is not None
