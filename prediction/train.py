"""Treino e avaliação do modelo preditivo de prazo (Fase 3).

Compara Regressão Linear e Árvore de Decisão, seleciona o melhor por RMSE/R²
no conjunto de teste e persiste modelo + transformer com ``joblib``.

Uso:
    uv run python prediction/train.py            # treina com default
    uv run python prediction/train.py --dados data/historico_importacoes.csv
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import joblib
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor

from prediction.preprocess import FeatureTransformer, carregar_dataset

logger = logging.getLogger("tradeflow.prediction.train")

RAIZ = Path(__file__).resolve().parents[1]
DEFAULT_DADOS = RAIZ / "data" / "historico_importacoes.csv"
DEFAULT_MODELO = RAIZ / "models" / "prazo_modelo.joblib"

# Candidatos de modelo: (nome, instância).
MODELOS: dict[str, object] = {
    "linear": LinearRegression(),
    "arvore": DecisionTreeRegressor(random_state=42, max_depth=8),
    "floresta": RandomForestRegressor(random_state=42, n_estimators=100, max_depth=10),
    "gradient": GradientBoostingRegressor(random_state=42, n_estimators=120, max_depth=4),
}


def treinar(
    dados: str | Path = DEFAULT_DADOS,
    saida: str | Path = DEFAULT_MODELO,
    test_size: float = 0.2,
) -> dict:
    """Treina, avalia e persiste o melhor modelo. Retorna as métricas."""
    df = carregar_dataset(dados)

    # Split ANTES de qualquer pré-processamento (evita data leakage).
    treino, teste = train_test_split(df, test_size=test_size, random_state=42)

    transformer = FeatureTransformer().fit(treino)
    X_treino = transformer.transform(treino)
    X_teste = transformer.transform(teste)
    y_treino = treino["prazo_desembaraco_dias"]
    y_teste = teste["prazo_desembaraco_dias"]

    melhor: tuple[str, float, object, dict] | None = None
    for nome, modelo in MODELOS.items():
        modelo.fit(X_treino, y_treino)
        pred = modelo.predict(X_teste)
        rmse = mean_squared_error(y_teste, pred) ** 0.5
        r2 = r2_score(y_teste, pred)
        mae = mean_absolute_error(y_teste, pred)
        logger.info(
            "modelo_avaliado",
            extra={"modelo": nome, "rmse": round(rmse, 2), "r2": round(r2, 3)},
        )
        if melhor is None or rmse < melhor[1]:
            melhor = (nome, rmse, modelo, {"rmse": rmse, "r2": r2, "mae": mae})

    assert melhor is not None
    nome, rmse, modelo, metricas = melhor

    # Persiste modelo + transformer no mesmo artefato.
    caminho = Path(saida)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"modelo": modelo, "transformer": transformer, "modelo_nome": nome}, caminho)

    metricas.update({"modelo_selecionado": nome, "artefato": str(caminho)})
    logger.info("modelo_salvo", extra=metricas)
    return metricas


def main() -> None:
    """CLI de treino."""
    parser = argparse.ArgumentParser(description="Treina o modelo de prazo de desembaraço")
    parser.add_argument("--dados", default=str(DEFAULT_DADOS))
    parser.add_argument("--saida", default=str(DEFAULT_MODELO))
    args = parser.parse_args()

    metricas = treinar(args.dados, args.saida)
    print(
        f"Modelo {metricas['modelo_selecionado']}: "
        f"RMSE={metricas['rmse']:.2f} R²={metricas['r2']:.3f} MAE={metricas['mae']:.2f} "
        f"-> {metricas['artefato']}"
    )


if __name__ == "__main__":
    main()
