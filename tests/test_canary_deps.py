"""Testes canary das dependências da Fase U2 (funcionais, sem custo).

Exercitam a API real de cada biblioteca para comprovar que o upgrade não
quebrou o uso que o TradeFlow fará delas.
"""

import io

import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sklearn.linear_model import LinearRegression


def test_sqlalchemy_crud_em_memoria() -> None:
    from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, select

    engine = create_engine("sqlite:///:memory:")
    meta = MetaData()
    tabela = Table(
        "importacoes",
        meta,
        Column("id", Integer, primary_key=True),
        Column("numero_fatura", String(50)),
        Column("valor_total", Integer),
    )
    meta.create_all(engine)

    with engine.begin() as conn:
        conn.execute(tabela.insert(), {"numero_fatura": "INV-001", "valor_total": 1000})
        row = conn.execute(select(tabela)).mappings().first()

    assert row is not None
    assert row["numero_fatura"] == "INV-001"
    assert row["valor_total"] == 1000


def test_fastapi_testclient() -> None:
    app = FastAPI()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    with TestClient(app) as client:
        resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_pypdf_e_pdfplumber_abrem_pdf() -> None:
    import pdfplumber
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)

    with pdfplumber.open(buf) as pdf:
        assert len(pdf.pages) == 1


def test_sklearn_pandas_treinam_modelo() -> None:
    df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [2.0, 4.0, 6.0, 8.0, 10.0]})
    modelo = LinearRegression().fit(df[["x"]], df["y"])
    previsao = modelo.predict([[6.0]])[0]
    assert abs(previsao - 12.0) < 1e-6


def test_pydantic_v2_continua_fun() -> None:
    from pydantic import BaseModel

    class Modelo(BaseModel):
        valor: float
        incoterm: str = "FOB"

    m = Modelo(valor="12.5")
    assert m.valor == 12.5
    assert m.incoterm == "FOB"
