"""Processamento assíncrono do pipeline (Fase 5) — worker em background.

A API enfileira o processamento e retorna 202 com o ID; o worker executa e
atualiza o status: ``pendente -> processando -> concluido/erro``.

Usa um ``ThreadPoolExecutor`` em processo (suficiente para o estágio; Celery
fica como evolução).
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from storage.db import session_scope
from storage.models import STATUS_CONCLUIDO, STATUS_ERRO, STATUS_PROCESSANDO
from storage.repositories import ImportacaoRepository

logger = logging.getLogger("tradeflow.jobs.worker")

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="tradeflow")


def enfileirar_processamento(pdf_path: str | Path, importacao_id: int) -> None:
    """Enfileira o processamento de um PDF no worker em background."""
    _executor.submit(_processar, Path(pdf_path), importacao_id)


def _processar(pdf_path: Path, importacao_id: int) -> None:
    """Executa o pipeline e atualiza o status do registro."""
    _marcar(importacao_id, STATUS_PROCESSANDO)
    try:
        from agents.pipeline import default_pipeline

        pipeline = default_pipeline()
        resultado = pipeline.process_pdf(pdf_path, importacao_id=importacao_id)
        if resultado.status == STATUS_CONCLUIDO:
            _marcar(importacao_id, STATUS_CONCLUIDO)
        else:
            _marcar(importacao_id, STATUS_ERRO, observacao=resultado.erro)
    except Exception as exc:  # noqa: BLE001 — erro estrutural do worker
        logger.exception("worker_erro", extra={"importacao_id": importacao_id})
        _marcar(importacao_id, STATUS_ERRO, observacao=str(exc))


def _marcar(importacao_id: int, status: str, *, observacao: str | None = None) -> None:
    """Atualiza o status no banco (com nova sessão)."""
    try:
        with session_scope() as sessao:
            ImportacaoRepository(sessao).update_status(importacao_id, status, observacao=observacao)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "worker_status_falhou",
            extra={"importacao_id": importacao_id, "erro": str(exc)},
        )
