"""API REST do TradeFlow (Fase 6).

Endpoints:
- ``POST /importacoes/upload`` — recebe PDF, enfileira o pipeline (202)
- ``GET  /importacoes/{id}`` — detalhe de uma importação
- ``GET  /importacoes/{id}/status`` — status consultável
- ``GET  /importacoes`` — listagem paginada
- ``GET  /health`` — healthcheck

Autenticação por ``X-API-Key`` (desabilitada se ``API_KEY`` vazia) e rate
limit via ``slowapi``.
"""

from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from api.schemas import ErroResponse, ImportacaoResponse, StatusResponse, UploadResponse
from config.settings import Settings, get_settings
from storage.db import session_scope
from storage.models import STATUS_PENDENTE
from storage.repositories import ImportacaoRepository

logger = logging.getLogger("tradeflow.api")

_RAIZ = Path(__file__).resolve().parents[1]
_UPLOAD_DIR = _RAIZ / "data" / "raw" / "uploads"


def _validate_api_key(settings: Settings) -> None:
    """Registra a dependência de autenticação por API key."""

    def dependencia(x_api_key: str | None = Header(default=None)) -> None:
        if settings.api_key and x_api_key != settings.api_key:
            raise HTTPException(status_code=401, detail="API key inválida")

    return dependencia


def create_app(settings: Settings | None = None) -> FastAPI:
    """Factory do app (permite injetar settings em testes)."""
    cfg = settings or get_settings()

    app = FastAPI(
        title=cfg.app_name,
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    # Rate limiting (slowapi).
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from slowapi.util import get_remote_address

        limiter = Limiter(key_func=get_remote_address, enabled=bool(cfg.api_rate_limit))
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    except ImportError:  # pragma: no cover — slowapi é dependência opcional
        limiter = None

    api_key_dep = _validate_api_key(cfg)

    # ------------------------------------------------------------ endpoints

    @app.get("/health", tags=["sistema"])
    def health() -> dict:
        return {"status": "ok", "app": cfg.app_name}

    @app.post(
        "/importacoes/upload",
        status_code=202,
        response_model=UploadResponse,
        responses={400: {"model": ErroResponse}, 401: {"model": ErroResponse}},
        tags=["importacoes"],
    )
    async def upload(
        request: Request,
        arquivo: UploadFile = File(...),  # noqa: B008 — padrão FastAPI
        _: None = Depends(api_key_dep),
    ) -> UploadResponse:
        _validar_upload(arquivo, cfg)

        # Salva o PDF em diretório temporário (nome sanitizado + uuid).
        ext = Path(arquivo.filename or "arquivo.pdf").suffix.lower()
        destino = _UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}"
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("wb") as saida:
            shutil.copyfileobj(arquivo.file, saida)

        # Cria registro pendente e enfileira o processamento.
        with session_scope() as sessao:
            importacao = ImportacaoRepository(sessao).create(
                numero_fatura=f"UPLOAD-{uuid.uuid4().hex[:8].upper()}",
                fornecedor=arquivo.filename or "desconhecido",
                observacao=f"upload={arquivo.filename or ''}",
            )
            importacao_id = importacao.id

        from jobs.worker import enfileirar_processamento

        enfileirar_processamento(destino, importacao_id)

        return UploadResponse(
            importacao_id=importacao_id,
            status=STATUS_PENDENTE,
            mensagem="Upload aceito — processamento em andamento.",
        )

    @app.get("/importacoes", response_model=list[ImportacaoResponse], tags=["importacoes"])
    def listar_importacoes(
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        _: None = Depends(api_key_dep),
    ) -> list[ImportacaoResponse]:
        with session_scope() as sessao:
            registros = ImportacaoRepository(sessao).list(limit=limit, offset=offset, status=status)
            return [ImportacaoResponse.model_validate(r) for r in registros]

    @app.get(
        "/importacoes/{importacao_id}",
        response_model=ImportacaoResponse,
        responses={404: {"model": ErroResponse}},
        tags=["importacoes"],
    )
    def obter_importacao(
        importacao_id: int,
        _: None = Depends(api_key_dep),
    ) -> ImportacaoResponse:
        with session_scope() as sessao:
            registro = ImportacaoRepository(sessao).get(importacao_id)
            if registro is None:
                raise HTTPException(status_code=404, detail="Importação não encontrada")
            return ImportacaoResponse.model_validate(registro)

    @app.get(
        "/importacoes/{importacao_id}/status",
        response_model=StatusResponse,
        responses={404: {"model": ErroResponse}},
        tags=["importacoes"],
    )
    def obter_status(
        importacao_id: int,
        _: None = Depends(api_key_dep),
    ) -> StatusResponse:
        with session_scope() as sessao:
            registro = ImportacaoRepository(sessao).get(importacao_id)
            if registro is None:
                raise HTTPException(status_code=404, detail="Importação não encontrada")
            return StatusResponse(
                importacao_id=registro.id,
                status=registro.status,
                observacao=registro.observacao,
            )

    # Handler de erros não tratados -> JSON consistente.
    @app.exception_handler(Exception)
    async def _erro_generico(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("api_erro_nao_tratado", exc_info=exc)
        return JSONResponse(status_code=500, content={"detalhe": "erro interno"})

    # HTTPException -> corpo padrão {"detalhe": ...} (consistente com ErroResponse).
    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detalhe": exc.detail})

    return app


def _validar_upload(arquivo: UploadFile, cfg: Settings) -> None:
    """Valida tipo/extensão e tamanho máximo do upload."""
    nome = arquivo.filename or ""
    ext = Path(nome).suffix.lower()
    if ext not in cfg.allowed_document_extensions:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Extensão não permitida: {ext or '(sem extensão)'}. "
                f"Permitidas: {cfg.allowed_document_extensions}"
            ),
        )

    tamanho_max = cfg.max_upload_size_mb * 1024 * 1024
    arquivo.file.seek(0, 2)
    tamanho = arquivo.file.tell()
    arquivo.file.seek(0)
    if tamanho > tamanho_max:
        raise HTTPException(
            status_code=400,
            detail=f"Arquivo excede {cfg.max_upload_size_mb} MB",
        )


app = create_app()
