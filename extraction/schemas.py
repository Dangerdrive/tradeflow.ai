"""Modelos de dados da extração de documentos (Commercial Invoice).

Define os contratos de saída da Fase 1: ``InvoiceData`` e ``InvoiceItem``.
A validação é feita com Pydantic v2 — tipos, formatos e domínios (ex.: incoterm).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# Incoterms 2020 válidos (subconjunto usado em importação marítima/aérea).
INCOTERMS_2020 = frozenset(
    {"EXW", "FCA", "FAS", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP"}
)


class Incoterm(StrEnum):
    """Incoterms 2020 suportados pelo TradeFlow."""

    EXW = "EXW"
    FCA = "FCA"
    FAS = "FAS"
    FOB = "FOB"
    CFR = "CFR"
    CIF = "CIF"
    CPT = "CPT"
    CIP = "CIP"
    DAP = "DAP"
    DPU = "DPU"
    DDP = "DDP"


class InvoiceItem(BaseModel):
    """Um item/linha da Commercial Invoice."""

    ncm: str | None = Field(
        default=None,
        description="Código NCM de 8 dígitos (ex.: 8528.72.00). Opcional na extração.",
    )
    descricao: str = Field(min_length=1, description="Descrição do produto.")
    quantidade: float = Field(gt=0, description="Quantidade do item.")
    valor: float = Field(ge=0, description="Valor do item em USD.")

    @field_validator("ncm")
    @classmethod
    def _valida_ncm(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # Aceita "8528.72.00", "85287200" ou "8528720000" — normaliza para 8 dígitos.
        digitos = v.replace(".", "").replace("-", "").replace(" ", "")
        if len(digitos) < 8 or not digitos.isdigit():
            raise ValueError(f"NCM inválido: {v!r}")
        return f"{digitos[:4]}.{digitos[4:6]}.{digitos[6:8]}"


class InvoiceData(BaseModel):
    """Campos estruturados extraídos de uma Commercial Invoice."""

    numero_fatura: str = Field(min_length=1, description="Número da fatura.")
    fornecedor: str = Field(min_length=1, description="Nome do fornecedor.")
    valor_total_usd: float = Field(ge=0, description="Valor total em USD.")
    peso_bruto_kg: float = Field(ge=0, default=0.0, description="Peso bruto em quilogramas.")
    incoterm: Incoterm = Field(description="Incoterm da operação.")
    volumes: int = Field(ge=0, default=0, description="Quantidade de volumes.")
    moeda: Literal["USD", "BRL", "EUR"] = Field(default="USD", description="Moeda da fatura.")
    itens: list[InvoiceItem] = Field(default_factory=list, description="Itens/linhas da fatura.")

    @field_validator("numero_fatura", "fornecedor")
    @classmethod
    def _limpa_texto(cls, v: str) -> str:
        return " ".join(v.split())

    @model_validator(mode="after")
    def _valida_consistencia(self) -> InvoiceData:
        # Se houver itens com valor, a soma não pode exceder o total (tolerância 1%).
        soma_itens = sum(i.valor for i in self.itens)
        if self.itens and self.valor_total_usd and soma_itens > self.valor_total_usd * 1.01:
            raise ValueError("A soma dos itens excede o valor total da fatura em mais de 1%")
        return self


# Aliases de contrato usados pelo orquestrador (interface estável).
ExtractionResult = InvoiceData
