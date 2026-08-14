"""Repositórios (padrão Repository) — Fase 4.

Encapsulam o acesso a dados das entidades ``Importacao`` e ``Item``,
desacoplando o resto do sistema da ORM.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from extraction.schemas import InvoiceData, InvoiceItem
from storage.models import STATUS_PENDENTE, Importacao, Item


class ImportacaoRepository:
    """Acesso a dados de ``Importacao``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------- escrita

    def create(self, *, numero_fatura: str, fornecedor: str, **campos) -> Importacao:
        """Cria e persiste uma importação (default status pendente)."""
        importacao = Importacao(
            numero_fatura=numero_fatura,
            fornecedor=fornecedor,
            status=campos.pop("status", STATUS_PENDENTE),
            **campos,
        )
        self._session.add(importacao)
        self._session.flush()
        return importacao

    def criar_de_invoice(self, dados: InvoiceData) -> Importacao:
        """Cria uma importação a partir do resultado da extração (Fase 1)."""
        importacao = self.create(
            numero_fatura=dados.numero_fatura,
            fornecedor=dados.fornecedor,
            valor_total_usd=dados.valor_total_usd,
            peso_bruto_kg=dados.peso_bruto_kg,
            incoterm=dados.incoterm.value,
            volumes=dados.volumes,
            moeda=dados.moeda,
            payload_bruto=dados.model_dump(mode="json"),
        )
        for item in dados.itens:
            self._session.add(
                Item(
                    importacao_id=importacao.id,
                    ncm=item.ncm,
                    descricao=item.descricao,
                    quantidade=item.quantidade,
                    valor=item.valor,
                )
            )
        self._session.flush()
        return importacao

    def update_status(
        self,
        importacao_id: int,
        status: str,
        *,
        observacao: str | None = None,
    ) -> Importacao | None:
        """Atualiza o status (e opcionalmente uma observação)."""
        importacao = self.get(importacao_id)
        if importacao is None:
            return None
        importacao.status = status
        if observacao is not None:
            importacao.observacao = observacao
        self._session.flush()
        return importacao

    def atualizar_resultado(
        self,
        importacao_id: int,
        *,
        ncm_sugerido: str | None = None,
        prazo_estimado_dias: int | None = None,
        status: str | None = None,
    ) -> Importacao | None:
        """Grava os resultados do pipeline (NCM e prazo) na importação."""
        importacao = self.get(importacao_id)
        if importacao is None:
            return None
        if ncm_sugerido is not None:
            importacao.ncm_sugerido = ncm_sugerido
        if prazo_estimado_dias is not None:
            importacao.prazo_estimado_dias = prazo_estimado_dias
        if status is not None:
            importacao.status = status
        self._session.flush()
        return importacao

    # -------------------------------------------------------------- leitura

    def get(self, importacao_id: int) -> Importacao | None:
        return self._session.get(Importacao, importacao_id)

    def find_by_fatura(self, numero_fatura: str, fornecedor: str) -> Importacao | None:
        """Busca por fatura+fornecedor (para idempotência)."""
        stmt = select(Importacao).where(
            Importacao.numero_fatura == numero_fatura,
            Importacao.fornecedor == fornecedor,
        )
        return self._session.scalar(stmt)

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
    ) -> list[Importacao]:
        stmt = (
            select(Importacao).order_by(Importacao.data_criacao.desc()).offset(offset).limit(limit)
        )
        if status:
            stmt = stmt.where(Importacao.status == status)
        return list(self._session.scalars(stmt))

    def count(self) -> int:
        return int(self._session.scalar(select(func.count(Importacao.id))) or 0)


class ItemRepository:
    """Acesso a dados de ``Item`` (complementar ao repositório de importação)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_by_importacao(self, importacao_id: int) -> list[Item]:
        stmt = select(Item).where(Item.importacao_id == importacao_id)
        return list(self._session.scalars(stmt))

    def add(self, importacao_id: int, item: InvoiceItem) -> Item:
        entidade = Item(
            importacao_id=importacao_id,
            ncm=item.ncm,
            descricao=item.descricao,
            quantidade=item.quantidade,
            valor=item.valor,
        )
        self._session.add(entidade)
        self._session.flush()
        return entidade
