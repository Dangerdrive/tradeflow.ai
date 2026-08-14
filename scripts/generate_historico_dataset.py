"""Gera o dataset sintético de histórico de importações (Fase 3).

Determinístico (seed fixa) para que treino/avaliação sejam reproduzíveis.
O prazo de desembaraço é modelado com uma função conhecida + ruído, o que
permite validar se o modelo recupera o padrão (sanity check do pipeline).

Colunas: incoterm, tipo_produto, peso_kg, valor_usd, volumes, prazo_desembaraco_dias

Uso:
    uv run python scripts/generate_historico_dataset.py
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ALVO = RAIZ / "data" / "historico_importacoes.csv"

INCOTERMS = ["EXW", "FOB", "CIF", "CFR", "DAP", "DDP"]
TIPOS = ["eletronicos", "texteis", "alimentos", "maquinas", "moveis", "auto"]

# Fator por incoterm: quanto maior, mais demorado (EXW/DAP costumam demorar mais).
FATOR_INCOTERM = {"EXW": 1.6, "FOB": 1.3, "CFR": 1.15, "CIF": 1.1, "DAP": 1.35, "DDP": 1.0}
# Fator por tipo: alguns tipos têm desembaraço mais lento (fiscalização).
FATOR_TIPO = {
    "eletronicos": 1.2,
    "texteis": 1.4,
    "alimentos": 1.1,
    "maquinas": 1.5,
    "moveis": 1.3,
    "auto": 1.25,
}


def main() -> None:
    """Gera o CSV com 500 linhas determinísticas."""
    rng = random.Random(42)

    linhas: list[dict] = []
    for _ in range(500):
        incoterm = rng.choice(INCOTERMS)
        tipo = rng.choice(TIPOS)
        peso_kg = round(rng.uniform(5, 5000), 1)
        valor_usd = round(rng.uniform(500, 60000), 2)
        volumes = rng.randint(1, 60)

        base = 6.0
        base += 3.0 * (peso_kg / 1000)  # peso atrasa
        base += 1.2 * (valor_usd / 10000)  # valor alto atrasa (fiscalização)
        base += 0.15 * volumes
        base *= FATOR_INCOTERM[incoterm]
        base *= FATOR_TIPO[tipo]
        prazo = int(round(base + rng.gauss(0, 2.0)))
        prazo = max(2, prazo)

        linhas.append(
            {
                "incoterm": incoterm,
                "tipo_produto": tipo,
                "peso_kg": peso_kg,
                "valor_usd": valor_usd,
                "volumes": volumes,
                "prazo_desembaraco_dias": prazo,
            }
        )

    with ALVO.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(
            arquivo,
            fieldnames=[
                "incoterm",
                "tipo_produto",
                "peso_kg",
                "valor_usd",
                "volumes",
                "prazo_desembaraco_dias",
            ],
        )
        escritor.writeheader()
        escritor.writerows(linhas)

    print(f"Dataset gerado: {ALVO} ({len(linhas)} linhas)")


if __name__ == "__main__":
    main()
