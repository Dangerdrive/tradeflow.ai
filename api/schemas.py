"""DTOs da API REST (Fase 6) — contratos de request/response."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImportacaoItemResponse(BaseModel):
    """Um item de importação na resposta da API."""

    model_config = ConfigDict(from_attributes=True)

    ncm: str | None
    descricao: str
    quantidade: float
    valor: float


class ImportacaoResponse(BaseModel):
    """Representação completa de uma importação."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_fatura: str
    fornecedor: str
    valor_total_usd: float
    peso_bruto_kg: float
    incoterm: str
    volumes: int
    moeda: str
    ncm_sugerido: str | None
    prazo_estimado_dias: int | None
    status: str
    observacao: str | None
    data_criacao: datetime
    data_atualizacao: datetime
    itens: list[ImportacaoItemResponse] = []


class UploadResponse(BaseModel):
    """Resposta do upload (202 Accepted — processamento em background)."""

    importacao_id: int
    status: str
    mensagem: str


class StatusResponse(BaseModel):
    """Status consultável de uma importação."""

    importacao_id: int
    status: str
    observacao: str | None = None


class ErroResponse(BaseModel):
    """Corpo padrão de erro."""

    detalhe: str
