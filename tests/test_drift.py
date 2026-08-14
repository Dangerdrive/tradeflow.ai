"""Testes do monitoramento de drift (Fase 8)."""

import numpy as np
import pandas as pd

from prediction.drift import (
    calcular_baseline,
    deve_retreinar,
    verificar_drift,
)
from prediction.preprocess import carregar_dataset

RAIZ = __import__("pathlib").Path(__file__).resolve().parents[1]
DATASET = RAIZ / "data" / "historico_importacoes.csv"


def _df(semente: int, n: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(semente)
    return pd.DataFrame(
        {
            "peso_kg": rng.uniform(5, 5000, n),
            "valor_usd": rng.uniform(500, 60000, n),
            "volumes": rng.integers(1, 60, n),
        }
    )


def test_sem_drift_nao_alerta() -> None:
    df_treino = _df(1)
    baseline = calcular_baseline(df_treino)
    relatorio = verificar_drift(df_treino, baseline)
    assert relatorio.alerta is False
    assert deve_retreinar(relatorio) is False


def test_drift_claro_alerta() -> None:
    df_treino = _df(1)
    baseline = calcular_baseline(df_treino)

    # Produção com features bem diferentes (peso muito maior).
    df_prod = df_treino.copy()
    df_prod["peso_kg"] = df_prod["peso_kg"] * 20

    relatorio = verificar_drift(df_prod, baseline)
    assert relatorio.alerta is True
    assert deve_retreinar(relatorio) is True
    assert "peso_kg" in relatorio.motivo


def test_baseline_do_dataset_real() -> None:
    df = carregar_dataset(DATASET)
    baseline = calcular_baseline(df)
    assert set(baseline.keys()) == {"peso_kg", "valor_usd", "volumes"}
    assert baseline["peso_kg"]["media"] > 0
