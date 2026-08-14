"""Seed do banco com dados de demonstração (Fase 4).

Insere algumas importações de exemplo (determinísticas, sem LLM) para a
demo/UI. Idempotente: usa a constraint única fatura+fornecedor.

Uso:
    uv run python scripts/seed_db.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from storage.db import create_session, init_db  # noqa: E402
from storage.models import STATUS_CONCLUIDO, STATUS_PENDENTE, STATUS_REVISADO  # noqa: E402
from storage.repositories import ImportacaoRepository  # noqa: E402

AMOSTRAS = [
    {
        "numero_fatura": "INV-2026-0842",
        "fornecedor": "Tech Global Ltd.",
        "valor_total_usd": 12850.40,
        "peso_bruto_kg": 320.5,
        "incoterm": "FOB",
        "volumes": 12,
        "ncm_sugerido": "8528.72.00",
        "prazo_estimado_dias": 9,
        "status": STATUS_CONCLUIDO,
    },
    {
        "numero_fatura": "FT-2026-1122",
        "fornecedor": "Logística BR Import",
        "valor_total_usd": 8900.00,
        "peso_bruto_kg": 150.0,
        "incoterm": "CIF",
        "volumes": 5,
        "ncm_sugerido": "9405.40.10",
        "prazo_estimado_dias": 12,
        "status": STATUS_REVISADO,
    },
    {
        "numero_fatura": "INV-2026-0199",
        "fornecedor": "Nordic Components AB",
        "valor_total_usd": 3240.00,
        "peso_bruto_kg": 88.0,
        "incoterm": "DAP",
        "volumes": 4,
        "ncm_sugerido": "8482.10.10",
        "prazo_estimado_dias": 15,
        "status": STATUS_PENDENTE,
    },
]


def main() -> None:
    """Popula o banco com as amostras (idempotente)."""
    init_db()
    sessao = create_session()
    try:
        repo = ImportacaoRepository(sessao)
        criadas = 0
        for amostra in AMOSTRAS:
            existente = repo.find_by_fatura(amostra["numero_fatura"], amostra["fornecedor"])
            if existente:
                continue
            repo.create(**amostra)
            criadas += 1
        sessao.commit()
        print(f"Seed concluído: {criadas} novas importações (total: {repo.count()})")
    finally:
        sessao.close()


if __name__ == "__main__":
    main()
