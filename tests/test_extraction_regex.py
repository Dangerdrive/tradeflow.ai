"""Testes do fallback determinístico por regex."""

import pytest

from extraction.regex_fallback import extract_fields_regex


def test_extrai_fatura_ingles() -> None:
    texto = """\
COMMERCIAL INVOICE
Invoice No.: INV-2026-0842
Supplier: Tech Global Ltd.
Total Amount: USD 12,850.40
Gross Weight: 320.5 kg
Incoterm: FOB
Volumes: 12
"""
    dados = extract_fields_regex(texto)
    assert dados.numero_fatura == "INV-2026-0842"
    assert dados.fornecedor == "Tech Global Ltd."
    assert dados.valor_total_usd == pytest.approx(12850.40)
    assert dados.peso_bruto_kg == pytest.approx(320.5)
    assert dados.incoterm.value == "FOB"
    assert dados.volumes == 12


def test_extrai_fatura_portugues() -> None:
    texto = """\
FATURA COMERCIAL
Nº Fatura: FT-2026-1122
Fornecedor: Logística BR Import
Valor Total: USD 8.900,00
Peso Bruto: 150 kg
Incoterm: CIF
Volumes: 5
"""
    dados = extract_fields_regex(texto)
    assert dados.numero_fatura == "FT-2026-1122"
    assert dados.fornecedor == "Logística BR Import"
    assert dados.valor_total_usd == pytest.approx(8900.00)
    assert dados.incoterm.value == "CIF"
    assert dados.volumes == 5


def test_campos_ausentes_ficam_com_default_e_nao_falham() -> None:
    dados = extract_fields_regex("Texto sem nenhum campo de fatura.")
    assert dados.numero_fatura == "DESCONHECIDA"
    assert dados.fornecedor == "DESCONHECIDO"
    assert dados.valor_total_usd == 0.0
    assert dados.incoterm.value == "FOB"


def test_detecta_incoterm_em_meio_do_texto() -> None:
    dados = extract_fields_regex("CONTRATO DE TRANSPORTE — condições: CIF Santos porto de destino.")
    assert dados.incoterm.value == "CIF"
