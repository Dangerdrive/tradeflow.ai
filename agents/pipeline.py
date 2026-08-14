"""Orquestração do pipeline TradeFlow (Fase 5).

Coordena extração -> classificação NCM -> predição de prazo -> persistência
(idempotente), registrando métricas de latência por etapa e tratando falhas
intermediárias (uma etapa falha não derruba as demais; erro é estruturado).

O pipeline usa os módulos de domínio diretamente (determinístico e testável).
O CrewAI equivalente está em ``agents/crew.py`` (para a demo).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from extraction.extractor import InvoiceExtractor
from extraction.regex_fallback import extract_fields_regex
from extraction.schemas import InvoiceData
from ncm.classifier import NcmClassifier, NcmSuggestion
from prediction.model import PrazoPredictor
from storage.db import session_scope
from storage.models import (
    STATUS_CONCLUIDO,
    STATUS_ERRO,
    STATUS_PENDENTE,
    Importacao,
    Item,
)
from storage.repositories import ImportacaoRepository

logger = logging.getLogger("tradeflow.agents.pipeline")


class Extrator(Protocol):
    """Contrato do componente de extração (Fase 1)."""

    def extract_from_pdf(self, pdf_path: str | Path, *, ocr: bool = False) -> InvoiceData: ...


@dataclass
class PipelineResult:
    """Resultado agregado do pipeline (DTO único)."""

    invoice: InvoiceData
    ncm_sugerido: NcmSuggestion | None = None
    prazo_estimado_dias: int | None = None
    status: str = STATUS_PENDENTE
    erro: str | None = None
    importacao_id: int | None = None
    metricas: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialização do resultado (para API/UI)."""
        return {
            "status": self.status,
            "erro": self.erro,
            "importacao_id": self.importacao_id,
            "numero_fatura": self.invoice.numero_fatura,
            "fornecedor": self.invoice.fornecedor,
            "ncm_sugerido": self.ncm_sugerido.ncm if self.ncm_sugerido else None,
            "prazo_estimado_dias": self.prazo_estimado_dias,
            "valor_total_usd": self.invoice.valor_total_usd,
            "metricas": self.metricas,
        }


class TradeFlowPipeline:
    """Pipeline completo: extrai, classifica, prevê e persiste."""

    def __init__(
        self,
        extrator: Extrator,
        classificador: NcmClassifier | None = None,
        preditor: PrazoPredictor | None = None,
    ) -> None:
        self.extrator = extrator
        self.classificador = classificador
        self.preditor = preditor

    # ------------------------------------------------------------ execução

    def process_pdf(
        self,
        pdf_path: str | Path,
        *,
        ocr: bool = False,
        importacao_id: int | None = None,
    ) -> PipelineResult:
        """Processa um PDF e retorna o resultado agregado (persiste no banco).

        Se ``importacao_id`` for informado, atualiza esse registro com os
        resultados (fluxo assíncrono da API); senão, persiste de forma
        idempotente pela chave fatura+fornecedor.
        """
        metricas: dict[str, float] = {}

        # 1) Extração — se falhar, erro claro e para.
        inicio = time.monotonic()
        try:
            invoice = self.extrator.extract_from_pdf(pdf_path, ocr=ocr)
        except Exception as exc:  # noqa: BLE001 — erro estruturado, sem crash
            logger.error("pipeline_erro_extracao", extra={"erro": str(exc)})
            return PipelineResult(
                invoice=InvoiceData(
                    numero_fatura="?",
                    fornecedor="?",
                    valor_total_usd=0.0,
                    incoterm="FOB",
                ),
                status=STATUS_ERRO,
                erro=f"Falha na extração: {exc}",
                metricas={"extracao_s": time.monotonic() - inicio},
            )
        metricas["extracao_s"] = time.monotonic() - inicio

        # 2) Classificação NCM — falha não derruba; segue sem NCM.
        ncm_sugerido: NcmSuggestion | None = None
        inicio = time.monotonic()
        if self.classificador is not None:
            try:
                descricao = _primeira_descricao(invoice)
                if descricao:
                    sugestoes = self.classificador.suggest_ncm(descricao, k=1)
                    ncm_sugerido = sugestoes[0] if sugestoes else None
            except Exception as exc:  # noqa: BLE001
                logger.warning("pipeline_erro_ncm", extra={"erro": str(exc)})
        metricas["ncm_s"] = time.monotonic() - inicio

        # 3) Predição de prazo — falha não derruba; segue sem prazo.
        prazo: int | None = None
        inicio = time.monotonic()
        if self.preditor is not None:
            try:
                prazo = self.preditor.predict(
                    peso_kg=invoice.peso_bruto_kg,
                    valor_usd=invoice.valor_total_usd,
                    volumes=invoice.volumes,
                    incoterm=invoice.incoterm.value,
                    tipo_produto=_tipo_produto(ncm_sugerido, invoice),
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("pipeline_erro_predicao", extra={"erro": str(exc)})
        metricas["predicao_s"] = time.monotonic() - inicio

        # 4) Persistência (idempotente ou sobre o registro informado).
        importacao_id_final: int | None = None
        inicio = time.monotonic()
        importacao = self._persistir(invoice, ncm_sugerido, prazo, importacao_id=importacao_id)
        if importacao is not None:
            importacao_id_final = importacao.id
        metricas["persistencia_s"] = time.monotonic() - inicio

        return PipelineResult(
            invoice=invoice,
            ncm_sugerido=ncm_sugerido,
            prazo_estimado_dias=prazo,
            status=STATUS_CONCLUIDO,
            importacao_id=importacao_id_final,
            metricas=metricas,
        )

    # -------------------------------------------------------- persistência

    def _persistir(
        self,
        invoice: InvoiceData,
        ncm: NcmSuggestion | None,
        prazo: int | None,
        *,
        importacao_id: int | None = None,
    ) -> Importacao | None:
        """Cria/atualiza a importação e retorna a entidade."""
        try:
            with session_scope() as sessao:
                repo = ImportacaoRepository(sessao)

                # Atualiza um registro existente (fluxo assíncrono) com tudo.
                if importacao_id is not None:
                    alvo = repo.get(importacao_id)
                    if alvo is not None:
                        alvo.numero_fatura = invoice.numero_fatura
                        alvo.fornecedor = invoice.fornecedor
                        alvo.valor_total_usd = invoice.valor_total_usd
                        alvo.peso_bruto_kg = invoice.peso_bruto_kg
                        alvo.incoterm = invoice.incoterm.value
                        alvo.volumes = invoice.volumes
                        alvo.moeda = invoice.moeda
                        alvo.payload_bruto = invoice.model_dump(mode="json")
                        alvo.ncm_sugerido = ncm.ncm if ncm else None
                        alvo.prazo_estimado_dias = prazo
                        alvo.status = STATUS_CONCLUIDO
                        alvo.itens.clear()
                        for item in invoice.itens:
                            alvo.itens.append(
                                Item(
                                    importacao_id=alvo.id,
                                    ncm=item.ncm,
                                    descricao=item.descricao,
                                    quantidade=item.quantidade,
                                    valor=item.valor,
                                )
                            )
                        sessao.flush()
                        return repo.get(importacao_id)

                # Idempotência pela chave fatura+fornecedor.
                existente = repo.find_by_fatura(invoice.numero_fatura, invoice.fornecedor)
                if existente is not None:
                    repo.atualizar_resultado(
                        existente.id,
                        ncm_sugerido=ncm.ncm if ncm else None,
                        prazo_estimado_dias=prazo,
                        status=STATUS_CONCLUIDO,
                    )
                    return repo.get(existente.id)

                importacao = repo.criar_de_invoice(invoice)
                repo.atualizar_resultado(
                    importacao.id,
                    ncm_sugerido=ncm.ncm if ncm else None,
                    prazo_estimado_dias=prazo,
                    status=STATUS_CONCLUIDO,
                )
                return importacao
        except Exception as exc:  # noqa: BLE001
            logger.error("pipeline_erro_persistencia", extra={"erro": str(exc)})
            return None


# ------------------------------------------------------------- factories


class _ExtratorSemLlm:
    """Extrator que usa o fallback regex diretamente (sem chave de API)."""

    def extract_from_pdf(self, pdf_path: str | Path, *, ocr: bool = False) -> InvoiceData:
        from extraction.parser import extract_text

        texto = extract_text(pdf_path, ocr=ocr)
        return extract_fields_regex(texto)


@lru_cache
def default_pipeline() -> TradeFlowPipeline:
    """Monta o pipeline com os componentes reais (conforme Settings).

    Sem ``OPENAI_API_KEY`` usa fallback regex + HashEmbedder; com chave usa
    LLM + OpenAIEmbeddings. O modelo de prazo é carregado se treinado.
    O resultado é cacheado — a indexação NCM é feita uma única vez.
    """
    from config.settings import get_settings
    from ncm.embedder import make_embedder
    from ncm.vector_store import InMemoryVectorStore, make_vector_store

    settings = get_settings()

    # Extrator: LLM se houver chave, senão regex puro.
    if settings.openai_api_key:
        from utils.llm import LlmClient

        llm = LlmClient(api_key=settings.openai_api_key, model=settings.openai_model)
        extrator: Extrator = InvoiceExtractor(llm)
    else:
        extrator = _ExtratorSemLlm()

    # Classificador NCM: embedder conforme chave; índice em memória (rápido).
    embedder = make_embedder(settings.openai_api_key)
    if settings.openai_api_key:
        vector_store = make_vector_store(settings.chroma_persist_dir)
    else:
        vector_store = InMemoryVectorStore()
    classificador = NcmClassifier(embedder, vector_store)
    from pathlib import Path as _Path

    _RAIZ = _Path(__file__).resolve().parents[1]
    classificador.index_tabela(_RAIZ / "data" / "tabela_ncm.csv")

    # Preditor: carrega o modelo se o artefato existir.
    preditor: PrazoPredictor | None = None
    artefato = _RAIZ / "models" / "prazo_modelo.joblib"
    if artefato.is_file():
        preditor = PrazoPredictor(artefato)

    return TradeFlowPipeline(extrator, classificador, preditor)


def _primeira_descricao(invoice: InvoiceData) -> str:
    """Usa a descrição do primeiro item (ou a da fatura) para o NCM."""
    if invoice.itens:
        return invoice.itens[0].descricao
    return f"{invoice.fornecedor} {invoice.numero_fatura}"


def _tipo_produto(ncm: NcmSuggestion | None, invoice: InvoiceData) -> str:
    """Mapeia para um tipo conhecido pelo modelo preditivo (heurística)."""
    if ncm and ncm.ncm:
        prefixo = ncm.ncm[:4]
        mapa = {
            "8528": "eletronicos",
            "8517": "eletronicos",
            "8471": "eletronicos",
            "9405": "eletronicos",
            "8536": "eletronicos",
            "8544": "eletronicos",
            "6109": "texteis",
            "6204": "texteis",
            "6203": "texteis",
            "0901": "alimentos",
            "1509": "alimentos",
            "8457": "maquinas",
            "8458": "maquinas",
            "8460": "maquinas",
            "8482": "maquinas",
            "4011": "auto",
            "4412": "moveis",
            "4410": "moveis",
            "9403": "moveis",
        }
        return mapa.get(prefixo, "eletronicos")
    return "eletronicos"
