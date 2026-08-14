"""Modelos ORM (SQLAlchemy 2.0) — Fase 4.

Tabelas ``importacoes`` e ``itens`` com:
- ``status``: pendente / processando / concluido / erro / revisado / corrigido
- ``payload_bruto``: JSON com a extração completa (auditabilidade)
- constraint única (numero_fatura, fornecedor) para idempotência
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storage.db import Base

# Status possíveis do ciclo de vida de uma importação.
STATUS_PENDENTE = "pendente"
STATUS_PROCESSANDO = "processando"
STATUS_CONCLUIDO = "concluido"
STATUS_ERRO = "erro"
STATUS_REVISADO = "revisado"
STATUS_CORRIGIDO = "corrigido"

STATUS_VALIDOS = frozenset(
    {
        STATUS_PENDENTE,
        STATUS_PROCESSANDO,
        STATUS_CONCLUIDO,
        STATUS_ERRO,
        STATUS_REVISADO,
        STATUS_CORRIGIDO,
    }
)


class Importacao(Base):
    """Uma importação processada (resultado agregado do pipeline)."""

    __tablename__ = "importacoes"
    __table_args__ = (
        UniqueConstraint("numero_fatura", "fornecedor", name="uq_importacao_fatura_fornecedor"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero_fatura: Mapped[str] = mapped_column(String(64), index=True)
    fornecedor: Mapped[str] = mapped_column(String(160))
    valor_total_usd: Mapped[float] = mapped_column(Float, default=0.0)
    peso_bruto_kg: Mapped[float] = mapped_column(Float, default=0.0)
    incoterm: Mapped[str] = mapped_column(String(8), default="FOB")
    volumes: Mapped[int] = mapped_column(Integer, default=0)
    moeda: Mapped[str] = mapped_column(String(3), default="USD")

    # Resultados do pipeline (Fases 2 e 3).
    ncm_sugerido: Mapped[str | None] = mapped_column(String(16), nullable=True)
    prazo_estimado_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Ciclo de vida e auditoria.
    status: Mapped[str] = mapped_column(String(16), default=STATUS_PENDENTE, index=True)
    payload_bruto: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_criacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    data_atualizacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    itens: Mapped[list[Item]] = relationship(
        back_populates="importacao",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover - repr informativo
        return f"<Importacao id={self.id} fatura={self.numero_fatura} status={self.status}>"


class Item(Base):
    """Item/linha de uma importação (extraído na Fase 1)."""

    __tablename__ = "itens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    importacao_id: Mapped[int] = mapped_column(
        ForeignKey("importacoes.id", ondelete="CASCADE"), index=True
    )
    ncm: Mapped[str | None] = mapped_column(String(16), nullable=True)
    descricao: Mapped[str] = mapped_column(String(255))
    quantidade: Mapped[float] = mapped_column(Float, default=1.0)
    valor: Mapped[float] = mapped_column(Float, default=0.0)

    importacao: Mapped[Importacao] = relationship(back_populates="itens")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Item id={self.id} ncm={self.ncm} descricao={self.descricao!r}>"
