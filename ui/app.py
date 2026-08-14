"""Interface Streamlit do TradeFlow (Fase 7) — Thin UI.

A lógica de negócio fica nas camadas de domínio (pipeline/repositórios);
aqui há apenas upload, exibição e ação de revisão humana.

Uso:
    streamlit run ui/app.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Streamlit roda `ui/app.py` com o diretório `ui/` no path — garante a raiz.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from agents.pipeline import default_pipeline
from storage.db import session_scope
from storage.models import STATUS_CONCLUIDO, STATUS_CORRIGIDO, STATUS_REVISADO
from storage.repositories import ImportacaoRepository

st.set_page_config(page_title="TradeFlow", page_icon="🚢", layout="wide")


def _cabecalho() -> None:
    st.title("🚢 TradeFlow — Agente de Despacho Aduaneiro")
    st.caption(
        "Upload de Commercial Invoice → extração → NCM (RAG) → prazo estimado → " "revisão humana."
    )


def _secao_upload() -> None:
    st.subheader("1. Processar uma fatura")
    arquivo = st.file_uploader("Envie um PDF de Commercial Invoice", type=["pdf"])

    if arquivo is not None and st.button("🚀 Processar", type="primary"):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(arquivo.getbuffer())
            caminho = Path(tmp.name)

        with st.spinner("Executando o pipeline (extração → NCM → prazo)..."):
            try:
                resultado = default_pipeline().process_pdf(caminho)
            except Exception as exc:  # noqa: BLE001 — falha de infraestrutura
                st.error(f"Falha ao processar: {exc}")
                return

        caminho.unlink(missing_ok=True)

        if resultado.status != STATUS_CONCLUIDO:
            st.error(f"Erro no processamento: {resultado.erro}")
            return

        st.success("Processamento concluído!")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Fatura", resultado.invoice.numero_fatura)
        col2.metric("Fornecedor", resultado.invoice.fornecedor)
        col3.metric("NCM sugerido", resultado.ncm_sugerido.ncm if resultado.ncm_sugerido else "—")
        col4.metric("Prazo estimado", f"{resultado.prazo_estimado_dias or '—'} dias")

        with st.expander("Detalhes da extração"):
            st.json(resultado.invoice.model_dump(mode="json"))
        if resultado.metricas:
            latencia = ", ".join(f"{k}={v:.2f}s" for k, v in resultado.metricas.items())
            st.caption(f"Latência por etapa: {latencia}")


def _secao_importacoes() -> None:
    st.subheader("2. Importações persistidas")
    with session_scope() as sessao:
        registros = ImportacaoRepository(sessao).list(limit=50)

    if not registros:
        st.info("Nenhuma importação ainda.")
        return

    st.dataframe(
        [
            {
                "ID": r.id,
                "Fatura": r.numero_fatura,
                "Fornecedor": r.fornecedor,
                "Valor (USD)": r.valor_total_usd,
                "NCM": r.ncm_sugerido or "—",
                "Prazo (dias)": r.prazo_estimado_dias or "—",
                "Status": r.status,
            }
            for r in registros
        ],
        width="stretch",
    )


def _secao_revisao() -> None:
    st.subheader("3. Revisão humana")
    with session_scope() as sessao:
        registros = ImportacaoRepository(sessao).list(limit=50)

    if not registros:
        return

    opcoes = {f"#{r.id} — {r.numero_fatura} ({r.fornecedor})": r.id for r in registros}
    escolha = st.selectbox("Selecione a importação", list(opcoes.keys()))
    importacao_id = opcoes[escolha]

    with session_scope() as sessao:
        registro = ImportacaoRepository(sessao).get(importacao_id)

    if registro is None:  # pragma: no cover
        return

    observacao = st.text_area("Observação (correção)", value=registro.observacao or "")

    col1, col2 = st.columns(2)
    if col1.button("✅ Marcar como revisado"):
        with session_scope() as sessao:
            ImportacaoRepository(sessao).update_status(importacao_id, STATUS_REVISADO)
        st.success("Marcado como revisado.")

    if col2.button("✏️ Marcar como corrigido"):
        with session_scope() as sessao:
            ImportacaoRepository(sessao).update_status(
                importacao_id, STATUS_CORRIGIDO, observacao=observacao or None
            )
        st.success("Marcado como corrigido.")


def main() -> None:
    """Renderiza a UI."""
    _cabecalho()
    _secao_upload()
    st.divider()
    _secao_importacoes()
    st.divider()
    _secao_revisao()


if __name__ == "__main__":
    main()
