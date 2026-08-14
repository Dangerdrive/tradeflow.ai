"""Testes da Fase 3 — modelo preditivo de prazo de desembaraço."""

import pytest

from prediction.model import PrazoPredictor
from prediction.preprocess import FeatureTransformer, carregar_dataset
from prediction.train import treinar

RAIZ = __import__("pathlib").Path(__file__).resolve().parents[1]
DATASET = RAIZ / "data" / "historico_importacoes.csv"


def test_treino_gera_metricas_razoaveis(tmp_path) -> None:
    saida = tmp_path / "modelo.joblib"
    metricas = treinar(DATASET, saida)
    assert metricas["r2"] > 0.8
    assert metricas["rmse"] < 5.0
    assert saida.is_file()


def test_predictor_preve_prazo_inteiro(tmp_path) -> None:
    saida = tmp_path / "modelo.joblib"
    treinar(DATASET, saida)

    predictor = PrazoPredictor(saida)
    prazo = predictor.predict(
        peso_kg=1200.0,
        valor_usd=15000.0,
        volumes=20,
        incoterm="CIF",
        tipo_produto="eletronicos",
    )
    assert isinstance(prazo, int)
    assert prazo >= 1


def test_predictor_inexistente_levanta_erro() -> None:
    with pytest.raises(FileNotFoundError):
        PrazoPredictor("/caminho/inexistente/modelo.joblib")


def test_preprocess_consistente_treino_inferencia() -> None:
    """Mesmo fit produz a mesma transformação (sem data leakage)."""
    df = carregar_dataset(DATASET).head(20)
    transformer = FeatureTransformer().fit(df)

    x1 = transformer.transform(df)
    x2 = transformer.transform(df)
    assert (x1 == x2).all()  # mesma saída para a mesma entrada


def test_carregar_dataset_valida_colunas() -> None:
    df = carregar_dataset(DATASET)
    esperadas = {
        "incoterm",
        "tipo_produto",
        "peso_kg",
        "valor_usd",
        "volumes",
        "prazo_desembaraco_dias",
    }
    assert esperadas.issubset(df.columns)
    assert len(df) > 100
