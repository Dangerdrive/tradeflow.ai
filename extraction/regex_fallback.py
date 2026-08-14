"""Fallback determinístico por regex para extração de Commercial Invoice.

Usado quando o LLM falha ou retorna JSON inválido. Extrai campos com
expressões regulares tolerantes a variações de layout e devolve um
``InvoiceData`` parcial (campos não encontrados ficam com valores padrão).

Padrão **Strategy**: ``extract_fields_regex`` tem a mesma interface do
extrator LLM — o orquestrador decide qual usar.
"""

from __future__ import annotations

import logging
import re

from extraction.schemas import INCOTERMS_2020, InvoiceData, InvoiceItem

logger = logging.getLogger("tradeflow.extraction.regex")

# Expressões regulares para os campos principais (case-insensitive).
# Usa [ \t]* entre rótulo e valor (não \s*) para nunca cruzar quebras de linha.
_RE_NUMERO_FATURA = re.compile(
    r"(?:invoice[ \t]*(?:no\.?|number|#)[ \t]*[:#]?[ \t]*"
    r"|invoice[ \t]*[:#][ \t]*"
    r"|n[º°]?[ \t]*fatura[ \t]*[:#]?[ \t]*"
    r"|fatura[ \t]*n[º°]?[ \t]*[:#]?[ \t]*)"
    r"([A-Z0-9][A-Z0-9\-/]{2,24})",
    re.IGNORECASE,
)
_RE_FORNECEDOR = re.compile(
    r"(?:supplier|vendor|seller|fornecedor)[ \t]*[:#]?[ \t]*"
    r"([A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9 .&\-]{3,60})",
    re.IGNORECASE,
)
_RE_VALOR_TOTAL = re.compile(
    r"(?:total[ \t]*(?:amount|value|invoice[ \t]*value)?|valor[ \t]*total)"
    r"[ \t]*[:#]?[ \t]*([A-Z]{3})?[ \t]*([0-9][0-9.,]{1,12})",
    re.IGNORECASE,
)
_RE_PESO = re.compile(
    r"(?:gross[ \t]*weight|peso[ \t]*bruto)[ \t]*[:#]?[ \t]*"
    r"([0-9][0-9.,]{1,8})[ \t]*(kg|kgs|quilogramas?)?",
    re.IGNORECASE,
)
_RE_VOLUMES = re.compile(
    r"(?:volumes?|packages?|vols?)[ \t]*[:#]?[ \t]*([0-9]{1,4})",
    re.IGNORECASE,
)
_RE_INCOTERM = re.compile(
    r"\b(" + "|".join(sorted(INCOTERMS_2020, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)
# Item: padrão "descricao - qtd un - USD valor" ou "descricao qtd x USD valor".
_RE_ITEM = re.compile(
    r"([A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9 /.\-]{3,80}?)\s+"
    r"(\d{1,5}(?:[.,]\d{3})*(?:,\d{1,2})?)\s*(?:x|un|pc|und|unid|cto)?\s*"
    r"(?:[-]?\s*(?:USD|US\$|EUR)\s*)?"
    r"(\d{1,5}(?:[.,]\d{3})*(?:,\d{2})?)",
    re.IGNORECASE,
)


def _para_float(texto: str) -> float:
    """Converte '12.850,40' ou '12850.40' para float (pt-BR ou en-US).

    Heurística de ambiguidade (fallback determinístico):
    - Com 3 dígitos após o único separador -> tratado como milhar
      ('1,240' = 1240; '5.600' = 5600) — formato pt-BR de milhar.
    - Caso contrário -> separador decimal ('45,5' = 45.5; '320.5' = 320.5).
    """
    texto = texto.strip()
    if "," in texto and "." in texto:
        # Ambos os separadores: o último é o decimal.
        if texto.rindex(",") > texto.rindex("."):
            texto = texto.replace(".", "").replace(",", ".")  # pt-BR
        else:
            texto = texto.replace(",", "")  # en-US
    elif "," in texto:
        # Só vírgula: 3 dígitos após = milhar; senão decimal.
        if len(texto.rsplit(",", 1)[1]) == 3:
            texto = texto.replace(",", "")
        else:
            texto = texto.replace(",", ".")
    elif "." in texto and len(texto.rsplit(".", 1)[1]) == 3:
        # Só ponto com 3 dígitos após o último = milhar pt-BR (5.600 = 5600).
        texto = texto.replace(".", "")
    return float(texto)


def extract_fields_regex(texto: str) -> InvoiceData:
    """Extrai campos de uma Commercial Invoice por regex.

    Nunca levanta exceção para texto inesperado — campos ausentes ficam com
    valores padrão e são logados como ``campos_nao_encontrados``.
    """
    campos_nao_encontrados: list[str] = []

    def _busca(padrao: re.Pattern[str], nome: str) -> re.Match[str] | None:
        m = padrao.search(texto)
        if m is None:
            campos_nao_encontrados.append(nome)
        return m

    numero = _busca(_RE_NUMERO_FATURA, "numero_fatura")
    fornecedor = _busca(_RE_FORNECEDOR, "fornecedor")
    total = _busca(_RE_VALOR_TOTAL, "valor_total_usd")
    peso = _busca(_RE_PESO, "peso_bruto_kg")
    volumes = _busca(_RE_VOLUMES, "volumes")
    incoterm = _busca(_RE_INCOTERM, "incoterm")

    itens: list[InvoiceItem] = []
    for m in _RE_ITEM.finditer(texto):
        descricao = m.group(1).strip().rstrip("-").strip()
        valor = _para_float(m.group(3))
        # Descarta ruído: descrição curta/débil ou valor não positivo.
        if valor <= 0 or len(descricao) < 4:
            continue
        if descricao.lower() in {"un", "usd", "eur", "total", "amount"}:
            continue
        itens.append(InvoiceItem(descricao=descricao, quantidade=1.0, valor=valor))

    # Moeda detectada junto ao valor total (ex.: "Total USD 1.234,50").
    moeda = "USD"
    if total is not None and total.group(1):
        moeda = total.group(1).upper()

    dados = InvoiceData(
        numero_fatura=numero.group(1) if numero else "DESCONHECIDA",
        fornecedor=fornecedor.group(1).strip() if fornecedor else "DESCONHECIDO",
        valor_total_usd=_para_float(total.group(2)) if total else 0.0,
        peso_bruto_kg=_para_float(peso.group(1)) if peso else 0.0,
        incoterm=(incoterm.group(0).upper() if incoterm else "FOB"),
        volumes=int(volumes.group(1)) if volumes else 0,
        moeda=moeda,
        itens=itens,
    )

    if campos_nao_encontrados:
        logger.warning(
            "regex_campos_nao_encontrados",
            extra={"campos": ",".join(campos_nao_encontrados)},
        )
    return dados


# Aliases compatíveis com a interface do extrator.
fallback_fields = extract_fields_regex
