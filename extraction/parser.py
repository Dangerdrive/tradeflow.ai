"""Leitura de PDFs e extração de texto (Fase 1).

Usa ``pdfplumber`` para extrair a camada de texto. Se o PDF for escaneado
(sem camada de texto), sinaliza para OCR via ``pytesseract``/``ocrmypdf``.

Padrão **Adapter**: ``extract_text`` é a interface estável; trocar o parser
não afeta quem consome.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("tradeflow.extraction.parser")

# Mínimo de caracteres de texto para considerar que o PDF tem camada de texto.
_MIN_TEXT_CHARS = 20


class PdfTextLayerMissingError(RuntimeError):
    """PDF sem camada de texto (escaneado) — requer OCR."""


class OcrUnavailableError(RuntimeError):
    """OCR solicitado, mas o binário ``tesseract`` não está disponível."""


def has_text_layer(pdf_path: str | Path) -> bool:
    """Retorna ``True`` se o PDF tem uma camada de texto mínima."""
    return len(extract_text(pdf_path)) >= _MIN_TEXT_CHARS


def extract_text(pdf_path: str | Path, *, ocr: bool = False) -> str:
    """Extrai o texto de um PDF.

    Args:
        pdf_path: caminho do arquivo PDF.
        ocr: se ``True`` e o PDF não tiver camada de texto, tenta OCR
            com ``pytesseract`` (requer ``tesseract`` instalado).

    Returns:
        Texto extraído, normalizado (espaços únicos por linha).

    Raises:
        PdfTextLayerMissingError: PDF sem camada de texto e ``ocr=False``.
        OcrUnavailableError: OCR requisitado mas indisponível.
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF não encontrado: {path}")

    texto = _extract_com_pdfplumber(path)

    if len(texto) < _MIN_TEXT_CHARS:
        if not ocr:
            raise PdfTextLayerMissingError(
                f"PDF sem camada de texto: {path.name}. Use ocr=True para escaneados."
            )
        texto = _extract_com_ocr(path)

    return _normalizar(texto)


def _extract_com_pdfplumber(path: Path) -> str:
    """Extrai a camada de texto com pdfplumber (imports lazy)."""
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - import garantido pelo pyproject
        raise RuntimeError("pdfplumber não instalado") from exc

    paginas: list[str] = []
    with pdfplumber.open(path) as pdf:
        for pagina in pdf.pages:
            # text é a camada de texto; se vazia, tenta extrair de chars/tables.
            t = pagina.extract_text() or ""
            paginas.append(t)
    return "\n".join(paginas)


def _extract_com_ocr(path: Path) -> str:
    """OCR via pytesseract (tesseract precisa estar no PATH do sistema)."""
    import importlib.util

    if importlib.util.find_spec("pytesseract") is None:
        raise OcrUnavailableError("pytesseract não instalado")
    if importlib.util.find_spec("pdf2image") is None:
        raise OcrUnavailableError("pdf2image não instalado (requer poppler)")

    import pdf2image
    import pytesseract

    try:
        imagens = pdf2image.convert_from_path(str(path))
    except Exception as exc:  # noqa: BLE001 — poppler ausente no sistema
        raise OcrUnavailableError("falha ao converter PDF (poppler ausente?)") from exc

    trechos: list[str] = []
    for imagem in imagens:
        try:
            trechos.append(pytesseract.image_to_string(imagem, lang="por"))
        except pytesseract.TesseractNotFoundError as exc:
            raise OcrUnavailableError("binário 'tesseract' não encontrado no PATH") from exc
    return "\n".join(trechos)


def _normalizar(texto: str) -> str:
    """Remove linhas vazias duplicadas e normaliza espaços."""
    linhas = [ln.strip() for ln in texto.splitlines()]
    # Remove linhas vazias consecutivas (mantém ao menos o conteúdo).
    resultado: list[str] = []
    for ln in linhas:
        if ln or (resultado and resultado[-1] != ""):
            resultado.append(ln)
    return "\n".join(resultado).strip()
