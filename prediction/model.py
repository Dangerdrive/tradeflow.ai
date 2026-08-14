"""Inferência do modelo preditivo de prazo (Fase 3).

Carrega o artefato (modelo + transformer) persistido por ``train.py`` e expõe
``PrazoPredictor.predict`` — a interface que o pipeline (Fase 5) consome.

A inferência usa exatamente o mesmo pré-processamento do treino.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

logger = logging.getLogger("tradeflow.prediction.model")

RAIZ = Path(__file__).resolve().parents[1]
DEFAULT_ARTEFATO = RAIZ / "models" / "prazo_modelo.joblib"


class PrazoPredictor:
    """Carrega o artefato e prevê o prazo de desembaraço em dias."""

    def __init__(self, artefato: str | Path = DEFAULT_ARTEFATO) -> None:
        caminho = Path(artefato)
        if not caminho.is_file():
            raise FileNotFoundError(
                f"Modelo não encontrado: {caminho}. Treine com `uv run python prediction/train.py`."
            )
        dados = joblib.load(caminho)
        self.modelo = dados["modelo"]
        self.transformer = dados["transformer"]
        self.modelo_nome = dados.get("modelo_nome", "desconhecido")

    def predict(
        self,
        *,
        peso_kg: float,
        valor_usd: float,
        volumes: int,
        incoterm: str,
        tipo_produto: str,
    ) -> int:
        """Prevê o prazo de desembaraço (dias) para os campos do pipeline."""
        df = pd.DataFrame(
            [
                {
                    "peso_kg": peso_kg,
                    "valor_usd": valor_usd,
                    "volumes": volumes,
                    "incoterm": incoterm,
                    "tipo_produto": tipo_produto,
                }
            ]
        )
        features = self.transformer.transform(df)
        pred = float(self.modelo.predict(features)[0])
        return max(1, int(round(pred)))


@lru_cache
def get_predictor(artefato: str | Path = DEFAULT_ARTEFATO) -> PrazoPredictor:
    """Retorna o predictor (cacheado) — evita re-carregar joblib a cada chamada."""
    return PrazoPredictor(artefato)


def predict_default(**campos) -> int:
    """Interface de conveniência usando o artefato default."""
    return get_predictor(DEFAULT_ARTEFATO).predict(**campos)
