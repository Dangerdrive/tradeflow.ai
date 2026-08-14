"""Estimativa de custo mensal de LLM (Fase 8, contenção de custos).

Mede os tokens médios por documento no golden dataset e projeta o custo
mensal com o modelo configurado (default gpt-4o-mini).

Referência de preço (gpt-4o-mini): US$ 0.15 / 1M tokens de entrada e
US$ 0.60 / 1M tokens de saída (valores típicos 2025-2026 — ajuste se mudar).

Uso:
    uv run python scripts/estimar_custo_llm.py [--docs-mes 1000]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extraction.extractor import _montar_prompt  # noqa: E402
from extraction.parser import extract_text  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SAMPLES = RAIZ / "data" / "raw" / "samples"

# Preços por 1M de tokens (USD) — gpt-4o-mini.
PRECO_ENTRADA_POR_1M = 0.15
PRECO_SAIDA_POR_1M = 0.60


def _contar_tokens(texto: str) -> int:
    """Conta tokens (tiktoken se disponível, senão estima por caracteres)."""
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(texto))
    except ImportError:  # pragma: no cover - fallback aproximado
        # Aproximação: ~4 caracteres por token em texto em PT/EN.
        return max(1, len(texto) // 4)


def main() -> None:
    """Calcula e imprime a estimativa de custo."""
    parser = argparse.ArgumentParser(description="Estima custo mensal de LLM")
    parser.add_argument("--docs-mes", type=int, default=1000)
    args = parser.parse_args()

    pdfs = sorted(SAMPLES.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"Nenhum PDF de amostra em {SAMPLES}")

    total_in = 0
    total_out = 0
    for pdf in pdfs:
        texto = extract_text(pdf)
        prompt = _montar_prompt(texto)
        total_in += _contar_tokens(prompt)
        # Saída estimada: ~2x o texto extraído (JSON completo com itens).
        total_out += _contar_tokens(texto) * 2

    n = len(pdfs)
    media_in = total_in / n
    media_out = total_out / n
    custo_doc = (
        media_in / 1_000_000 * PRECO_ENTRADA_POR_1M + media_out / 1_000_000 * PRECO_SAIDA_POR_1M
    )
    custo_mensal = custo_doc * args.docs_mes

    print(f"Amostras: {n} PDFs | Modelo: gpt-4o-mini (cache + retry ativos)")
    print(f"Tokens médios/entrada: {media_in:.0f} | saída: {media_out:.0f}")
    print(f"Custo por documento: US$ {custo_doc:.5f}")
    print(f"Custo mensal ({args.docs_mes} docs): US$ {custo_mensal:.2f}")
    print(
        "Mitigações: cache por prompt (utils/llm.py), max_tokens limitado, "
        "fallback regex quando aplicável."
    )


if __name__ == "__main__":
    main()
