"""Monitoramento de drift de features do modelo preditivo (Fase 8).

Compara as features de produção com a distribuição do treino (baseline).
Se alguma feature numérica desvia além do limite (z-score), aciona alerta de
retreino. Simples e sem dependências adicionais (usa pandas).

Uso (em um job periódico):
    baseline = calcular_baseline(df_treino)
    relatorio = verificar_drift(df_producao, baseline)
    if relatorio.alerta:
        # disparar retreino / alerta
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

# Features numéricas monitoradas.
FEATURES_NUMERICAS = ["peso_kg", "valor_usd", "volumes"]
# Limite de z-score para acionar alerta.
_LIMITE_Z = 3.0


@dataclass
class RelatorioDrift:
    """Resultado da verificação de drift."""

    alerta: bool
    features: dict[str, dict] = field(default_factory=dict)
    motivo: str | None = None

    def to_dict(self) -> dict:
        return {"alerta": self.alerta, "features": self.features, "motivo": self.motivo}


def calcular_baseline(df: pd.DataFrame) -> dict:
    """Calcula média/desvio das features numéricas do conjunto de treino."""
    baseline: dict[str, dict] = {}
    for coluna in FEATURES_NUMERICAS:
        serie = df[coluna].dropna()
        baseline[coluna] = {
            "media": float(serie.mean()),
            "desvio": float(serie.std(ddof=1)) if len(serie) > 1 else 0.0,
        }
    return baseline


def verificar_drift(
    df_producao: pd.DataFrame,
    baseline: dict,
    limite_z: float = _LIMITE_Z,
) -> RelatorioDrift:
    """Compara a produção com o baseline e reporta desvios.

    Para cada feature, calcula o z-score da média de produção em relação à
    distribuição do baseline. |z| > ``limite_z`` aciona alerta.
    """
    features: dict[str, dict] = {}
    alertas: list[str] = []

    for coluna in FEATURES_NUMERICAS:
        base = baseline.get(coluna)
        if base is None or base["desvio"] == 0 or coluna not in df_producao:
            continue
        serie = df_producao[coluna].dropna()
        if serie.empty:
            continue
        n = len(serie)
        media_prod = float(serie.mean())
        # Erro padrão da média de produção.
        erro_padrao = base["desvio"] / math.sqrt(n)
        z = (media_prod - base["media"]) / erro_padrao if erro_padrao > 0 else 0.0
        features[coluna] = {"media_prod": media_prod, "media_base": base["media"], "z": round(z, 2)}
        if abs(z) > limite_z:
            alertas.append(f"{coluna}: z={z:.2f}")

    motivo = "; ".join(alertas) if alertas else None
    return RelatorioDrift(alerta=bool(alertas), features=features, motivo=motivo)


def deve_retreinar(relatorio: RelatorioDrift) -> bool:
    """Decide se o modelo deve ser retreinado com base no relatório."""
    return relatorio.alerta
