"""Fixtures de teste — geração de PDFs mínimos válidos com texto (v3).

Cria PDFs de 1 página com camada de texto usando a sintaxe PDF diretamente
(sem dependências extras como reportlab), com xref correta e **ToUnicode CMap**
para que acentos (º, í, ç, –) sejam extraídos corretamente por
``pdfplumber``/``pdfminer``.
"""

from __future__ import annotations


def _escape_text(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_tounicode_cmap() -> bytes:
    """Gera um ToUnicode CMap (byte 0x20..0xFF -> Unicode) para cp1252."""
    linhas: list[bytes] = [
        b"/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n",
        b"/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n",
        b"/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n",
        b"1 begincodespacerange\n<00> <FF>\nendcodespacerange\n",
    ]
    pares: list[str] = []
    for code in range(0x20, 0x100):
        ch = bytes([code]).decode("cp1252", errors="replace")
        unicode_cp = ord(ch) if ch != "\ufffd" else code
        pares.append(f"<{code:02X}> <{unicode_cp:04X}>")
    for i in range(0, len(pares), 100):
        bloco = pares[i : i + 100]
        linhas.append(f"{len(bloco)} beginbfchar\n".encode())
        linhas.extend(f"{par}\n".encode() for par in bloco)
        linhas.append(b"endbfchar\n")
    linhas.append(b"endcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n")
    return b"".join(linhas)


def make_pdf(lines: list[str]) -> bytes:
    """Gera um PDF de 1 página contendo ``lines`` como texto legível."""
    content = ["BT", "/F1 12 Tf"]
    for i, line in enumerate(lines):
        y = 720 - i * 18
        content.append(f"1 0 0 1 72 {y} Tm ({_escape_text(line)}) Tj")
    content.append("ET")
    stream = "\n".join(content).encode("cp1252", errors="replace")
    cmap = _build_tounicode_cmap()

    # Monta os objetos do PDF (com xref correta no final).
    objetos: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        b"/Encoding /WinAnsiEncoding /ToUnicode 6 0 R >>",
        b"<< /Length " + str(len(cmap)).encode() + b" >>\nstream\n" + cmap + b"\nendstream",
    ]

    corpo = bytearray(b"%PDF-1.4\n")
    for i, obj in enumerate(objetos, start=1):
        corpo += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"

    # Calcula offsets reais de cada objeto para a xref.
    offsets = [0]
    for i in range(1, len(objetos) + 1):
        marker = f"{i} 0 obj\n".encode()
        offsets.append(corpo.index(marker, offsets[-1]))

    xref = bytearray(b"xref\n0 7\n0000000000 65535 f \n")
    for off in offsets[1:]:
        xref += f"{off:010d} 00000 n \n".encode()

    corpo += (
        b"trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n" + str(len(corpo)).encode() + b"\n%%EOF\n"
    )
    return bytes(corpo) + bytes(xref)


# ---------------------------------------------------------------------------
# Conteúdos de exemplo (golden/samples) usados nos testes e no dataset.

INVOICE_EN = [
    "COMMERCIAL INVOICE",
    "Invoice No.: INV-2026-0842",
    "Supplier: Tech Global Ltd.",
    "Total Amount: USD 12,850.40",
    "Gross Weight: 320.5 kg",
    "Incoterm: FOB",
    "Volumes: 12",
    'Televisor LED 55" - 10 un - USD 12,850.40',
]

INVOICE_PT = [
    "FATURA COMERCIAL",
    "Nº Fatura: FT-2026-1122",
    "Fornecedor: Logística BR Import",
    "Valor Total: USD 8.900,00",
    "Peso Bruto: 150 kg",
    "Incoterm: CIF",
    "Volumes: 5",
    "Lampada LED 9W - 500 un - USD 4.450,00",
    "Cabo USB-C 2m - 1000 un - USD 4.450,00",
]

INVOICE_BLANK = []  # PDF sem camada de texto (simula escaneado).
