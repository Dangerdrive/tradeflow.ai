"""Pré-processamento de features para o modelo preditivo (Fase 3).

Encapsula a transformação de features (one-hot de categóricas + escala de
numéricas) num pipeline único treino/inferência, evitando *data leakage*:
o mesmo ``fit`` é usado no treino e na inferência.
"""

from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Colunas esperadas (interface estável entre treino e inferência).
COLUNAS_NUMERICAS = ["peso_kg", "valor_usd", "volumes"]
COLUNAS_CATEGORICAS = ["incoterm", "tipo_produto"]

COLS = COLUNAS_NUMERICAS + COLUNAS_CATEGORICAS


class FeatureTransformer:
    """Pipeline de features — fit no treino, transform no treino/inferência."""

    def __init__(self) -> None:
        self._pipeline = Pipeline(
            steps=[
                (
                    "features",
                    ColumnTransformer(
                        transformers=[
                            ("num", StandardScaler(), COLUNAS_NUMERICAS),
                            ("cat", OneHotEncoder(handle_unknown="ignore"), COLUNAS_CATEGORICAS),
                        ]
                    ),
                )
            ]
        )

    def fit(self, df: pd.DataFrame) -> FeatureTransformer:
        self._pipeline.fit(df[COLS])
        return self

    def transform(self, df: pd.DataFrame):
        return self._pipeline.transform(df[COLS])

    def feature_names(self) -> list[str]:
        """Nomes das colunas transformadas (para inspeção)."""
        steps = self._pipeline.named_steps["features"]
        nomes_num = COLUNAS_NUMERICAS
        nomes_cat = (
            steps.named_transformers_["cat"].get_feature_names_out(COLUNAS_CATEGORICAS).tolist()
        )
        return nomes_num + nomes_cat


def carregar_dataset(caminho: str) -> pd.DataFrame:
    """Carrega o CSV de histórico validando as colunas esperadas."""
    df = pd.read_csv(caminho)
    faltantes = [c for c in COLS + ["prazo_desembaraco_dias"] if c not in df.columns]
    if faltantes:
        raise ValueError(f"Colunas ausentes no dataset: {faltantes}")
    return df.dropna(subset=COLS + ["prazo_desembaraco_dias"])
