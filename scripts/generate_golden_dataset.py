"""Gera o golden dataset de amostras (PDFs de fatura anotados) — Fase 1.

Cria 10 PDFs sintéticos de Commercial Invoice em ``data/raw/samples/`` e o
arquivo de ground truth ``data/golden/golden_annotations.json`` (fatura ->
campos esperados). Usado para medir a precisão da extração (meta >= 90%).

Uso:
    uv run python scripts/generate_golden_dataset.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Fixture de geração de PDF (reutiliza o helper dos testes).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.fixtures.sample_pdf import make_pdf  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SAMPLES_DIR = RAIZ / "data" / "raw" / "samples"
GOLDEN_DIR = RAIZ / "data" / "golden"

# (nome_arquivo, linhas_do_pdf, ground_truth)
AMOSTRAS: list[tuple[str, list[str], dict]] = [
    (
        "invoice_001.pdf",
        [
            "COMMERCIAL INVOICE",
            "Invoice No.: INV-2026-0842",
            "Supplier: Tech Global Ltd.",
            "Total Amount: USD 12,850.40",
            "Gross Weight: 320.5 kg",
            "Incoterm: FOB",
            "Volumes: 12",
            'Televisor LED 55" - 10 un - USD 12,850.40',
        ],
        {
            "numero_fatura": "INV-2026-0842",
            "fornecedor": "Tech Global Ltd.",
            "valor_total_usd": 12850.40,
            "peso_bruto_kg": 320.5,
            "incoterm": "FOB",
            "volumes": 12,
        },
    ),
    (
        "invoice_002.pdf",
        [
            "FATURA COMERCIAL",
            "Nº Fatura: FT-2026-1122",
            "Fornecedor: Logística BR Import",
            "Valor Total: USD 8.900,00",
            "Peso Bruto: 150 kg",
            "Incoterm: CIF",
            "Volumes: 5",
            "Lampada LED 9W - 500 un - USD 4.450,00",
            "Cabo USB-C 2m - 1000 un - USD 4.450,00",
        ],
        {
            "numero_fatura": "FT-2026-1122",
            "fornecedor": "Logística BR Import",
            "valor_total_usd": 8900.00,
            "peso_bruto_kg": 150.0,
            "incoterm": "CIF",
            "volumes": 5,
        },
    ),
    (
        "invoice_003.pdf",
        [
            "COMMERCIAL INVOICE",
            "Invoice No: INV-2026-0199",
            "Seller: Nordic Components AB",
            "Total Invoice Value: USD 3,240.00",
            "Gross Weight: 88 kg",
            "Incoterm: DAP",
            "Packages: 4",
            "Steel bearing 6204 - 2000 un - USD 3,240.00",
        ],
        {
            "numero_fatura": "INV-2026-0199",
            "fornecedor": "Nordic Components AB",
            "valor_total_usd": 3240.00,
            "peso_bruto_kg": 88.0,
            "incoterm": "DAP",
            "volumes": 4,
        },
    ),
    (
        "invoice_004.pdf",
        [
            "COMMERCIAL INVOICE",
            "Invoice #: INV-2026-0311",
            "Vendor: Asia Pacific Electronics",
            "Total: USD 22,110.75",
            "Gross Weight: 745.2 kg",
            "Incoterm: CIF",
            "Volumes: 26",
            'Smartphone 6.1" - 500 un - USD 22,110.75',
        ],
        {
            "numero_fatura": "INV-2026-0311",
            "fornecedor": "Asia Pacific Electronics",
            "valor_total_usd": 22110.75,
            "peso_bruto_kg": 745.2,
            "incoterm": "CIF",
            "volumes": 26,
        },
    ),
    (
        "invoice_005.pdf",
        [
            "FATURA COMERCIAL",
            "Fatura Nº: FT-2026-2055",
            "Fornecedor: Indústrias Andinas",
            "Valor Total: USD 5.678,90",
            "Peso Bruto: 210 kg",
            "Incoterm: EXW",
            "Volumes: 8",
            "Café torrado 1kg - 300 un - USD 2.839,45",
            "Café torrado 500g - 400 un - USD 2.839,45",
        ],
        {
            "numero_fatura": "FT-2026-2055",
            "fornecedor": "Indústrias Andinas",
            "valor_total_usd": 5678.90,
            "peso_bruto_kg": 210.0,
            "incoterm": "EXW",
            "volumes": 8,
        },
    ),
    (
        "invoice_006.pdf",
        [
            "COMMERCIAL INVOICE",
            "Invoice No.: INV-2026-0440",
            "Supplier: Rhein Machinery GmbH",
            "Total Amount: USD 47,500.00",
            "Gross Weight: 1,240 kg",
            "Incoterm: FOB",
            "Volumes: 2",
            "CNC milling machine - 1 un - USD 47,500.00",
        ],
        {
            "numero_fatura": "INV-2026-0440",
            "fornecedor": "Rhein Machinery GmbH",
            "valor_total_usd": 47500.00,
            "peso_bruto_kg": 1240.0,
            "incoterm": "FOB",
            "volumes": 2,
        },
    ),
    (
        "invoice_007.pdf",
        [
            "FATURA COMERCIAL",
            "Nº Fatura: FT-2026-0777",
            "Fornecedor: Têxtil Vale do Itajaí",
            "Valor Total: USD 1.890,60",
            "Peso Bruto: 45,5 kg",
            "Incoterm: DDP",
            "Volumes: 3",
            "Camiseta algodão 100% - 800 un - USD 1.890,60",
        ],
        {
            "numero_fatura": "FT-2026-0777",
            "fornecedor": "Têxtil Vale do Itajaí",
            "valor_total_usd": 1890.60,
            "peso_bruto_kg": 45.5,
            "incoterm": "DDP",
            "volumes": 3,
        },
    ),
    (
        "invoice_008.pdf",
        [
            "COMMERCIAL INVOICE",
            "Invoice No.: INV-2026-0555",
            "Supplier: Gulf Food Trading",
            "Total Amount: USD 9,412.30",
            "Gross Weight: 980 kg",
            "Incoterm: CFR",
            "Volumes: 40",
            "Olive oil 5L - 600 un - USD 9,412.30",
        ],
        {
            "numero_fatura": "INV-2026-0555",
            "fornecedor": "Gulf Food Trading",
            "valor_total_usd": 9412.30,
            "peso_bruto_kg": 980.0,
            "incoterm": "CFR",
            "volumes": 40,
        },
    ),
    (
        "invoice_009.pdf",
        [
            "COMMERCIAL INVOICE",
            "Invoice No.: INV-2026-0666",
            "Supplier: Silicon Valley Components",
            "Total Amount: USD 18,200.00",
            "Gross Weight: 12.8 kg",
            "Incoterm: CIP",
            "Volumes: 1",
            "GPU workstation - 2 un - USD 18,200.00",
        ],
        {
            "numero_fatura": "INV-2026-0666",
            "fornecedor": "Silicon Valley Components",
            "valor_total_usd": 18200.00,
            "peso_bruto_kg": 12.8,
            "incoterm": "CIP",
            "volumes": 1,
        },
    ),
    (
        "invoice_010.pdf",
        [
            "FATURA COMERCIAL",
            "Nº Fatura: FT-2026-0999",
            "Fornecedor: Madeiras do Norte",
            "Valor Total: USD 7.350,00",
            "Peso Bruto: 5.600 kg",
            "Incoterm: FOB",
            "Volumes: 15",
            "Compensado 18mm - 50 un - USD 7.350,00",
        ],
        {
            "numero_fatura": "FT-2026-0999",
            "fornecedor": "Madeiras do Norte",
            "valor_total_usd": 7350.00,
            "peso_bruto_kg": 5600.0,
            "incoterm": "FOB",
            "volumes": 15,
        },
    ),
]


def main() -> None:
    """Gera os PDFs e o arquivo de anotações."""
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    anotacoes: dict[str, dict] = {}
    for nome, linhas, verdade in AMOSTRAS:
        pdf_bytes = make_pdf(linhas)
        (SAMPLES_DIR / nome).write_bytes(pdf_bytes)
        anotacoes[nome] = verdade

    alvo = GOLDEN_DIR / "golden_annotations.json"
    alvo.write_text(json.dumps(anotacoes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Gerados {len(AMOSTRAS)} PDFs em {SAMPLES_DIR}")
    print(f"Anotações em {alvo}")


if __name__ == "__main__":
    main()
