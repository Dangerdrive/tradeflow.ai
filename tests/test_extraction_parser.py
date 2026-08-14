"""Testes do parser de PDF (pdfplumber + detecção de camada de texto)."""

import pytest

from extraction.parser import (
    PdfTextLayerMissingError,
    extract_text,
    has_text_layer,
)
from tests.fixtures.sample_pdf import INVOICE_EN, INVOICE_PT, make_pdf


def test_extrai_texto_de_pdf_com_camada_de_texto(tmp_path) -> None:
    pdf = tmp_path / "invoice.pdf"
    pdf.write_bytes(make_pdf(INVOICE_EN))

    texto = extract_text(pdf)
    assert "COMMERCIAL INVOICE" in texto
    assert "INV-2026-0842" in texto


def test_has_text_layer_detecta_camada(tmp_path) -> None:
    pdf = tmp_path / "invoice.pdf"
    pdf.write_bytes(make_pdf(INVOICE_EN))
    assert has_text_layer(pdf) is True


def test_pdf_sem_camada_de_texto_levanta_erro(tmp_path) -> None:
    pdf = tmp_path / "blank.pdf"
    pdf.write_bytes(make_pdf([]))
    with pytest.raises(PdfTextLayerMissingError):
        extract_text(pdf)


def test_pdf_inexistente_levanta_filenotfound() -> None:
    with pytest.raises(FileNotFoundError):
        extract_text("/caminho/inexistente/nao-existe.pdf")


def test_extrai_pdf_em_portugues(tmp_path) -> None:
    pdf = tmp_path / "invoice_pt.pdf"
    pdf.write_bytes(make_pdf(INVOICE_PT))
    texto = extract_text(pdf)
    assert "FATURA COMERCIAL" in texto
    assert "FT-2026-1122" in texto
