"""Avalia a precisão da extração no golden dataset (Fase 1).

Roda o fallback determinístico (regex) contra as 10 faturas anotadas em
``data/golden/golden_annotations.json`` e reporta a acurácia por campo e
por documento. Meta do plano: >= 90% de documentos com os 6 campos corretos.

O caminho LLM (extrator completo) tende a superar o regex; este script mede
o baseline determinístico sem custo de tokens.

Uso:
    uv run python scripts/evaluate_extraction.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Garante que a raiz do projeto está no path (script roda via `uv run python ...`).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extraction.parser import extract_text  # noqa: E402
from extraction.regex_fallback import extract_fields_regex  # noqa: E402
from extraction.schemas import InvoiceData  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SAMPLES_DIR = RAIZ / "data" / "raw" / "samples"
ANOTACOES = RAIZ / "data" / "golden" / "golden_annotations.json"

# Campos avaliados (Fase 1 pede 6 campos).
CAMPOS = ["numero_fatura", "fornecedor", "valor_total_usd", "peso_bruto_kg", "incoterm", "volumes"]


def _valor_normalizado(esperado: object, obtido: object) -> bool:
    if isinstance(esperado, float):
        return abs(float(obtido) - esperado) < 0.01
    return str(esperado).lower() == str(obtido).lower()


def main() -> None:
    """Roda a avaliação e imprime o relatório."""
    anotacoes = json.loads(ANOTACOES.read_text(encoding="utf-8"))

    acertos_por_campo = {c: 0 for c in CAMPOS}
    total_docs = len(anotacoes)
    docs_completos = 0

    for nome, verdade in sorted(anotacoes.items()):
        texto = extract_text(SAMPLES_DIR / nome)
        dados: InvoiceData = extract_fields_regex(texto)
        acertos = 0
        for campo in CAMPOS:
            if _valor_normalizado(verdade[campo], getattr(dados, campo)):
                acertos_por_campo[campo] += 1
                acertos += 1
        if acertos == len(CAMPOS):
            docs_completos += 1
        status = "OK " if acertos == len(CAMPOS) else f"{acertos}/6"
        print(f"{nome}: {status}")

    print("\n=== Resumo (regex fallback) ===")
    for campo in CAMPOS:
        pct = 100.0 * acertos_por_campo[campo] / total_docs
        print(f"  {campo}: {acertos_por_campo[campo]}/{total_docs} ({pct:.0f}%)")
    pct_docs = 100.0 * docs_completos / total_docs
    print(f"Documentos com 6/6 campos: {docs_completos}/{total_docs} ({pct_docs:.0f}%)")
    print("Meta Fase 1: >= 90% dos documentos com 6/6 (com LLM o resultado melhora).")


if __name__ == "__main__":
    main()
