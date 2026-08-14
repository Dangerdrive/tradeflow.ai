"""Camada de banco de dados (Fase 4): engine, session e Base declarativa.

Trocar SQLite por PostgreSQL muda apenas ``DATABASE_URL`` (via
``config.settings``) — o código de repositórios não muda.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base declarativa de todos os modelos ORM do TradeFlow."""


@lru_cache
def get_engine(url: str | None = None) -> Engine:
    """Retorna o engine (cacheado). Default: URL de config.settings."""
    if url is None:
        from config.settings import get_settings

        url = get_settings().database_url

    # SQLite precisa de connect_args para permitir threads (FastAPI/Streamlit).
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


@lru_cache
def get_session_factory(url: str | None = None) -> sessionmaker[Session]:
    """Retorna a factory de sessões (cacheada) para o URL informado."""
    engine = get_engine(url)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_session(url: str | None = None) -> Session:
    """Cria uma sessão nova (para uso direto fora de contexto)."""
    return get_session_factory(url)()


@contextmanager
def session_scope(url: str | None = None) -> Iterator[Session]:
    """Contexto de sessão com commit/rollback automático."""
    sessao = create_session(url)
    try:
        yield sessao
        sessao.commit()
    except Exception:
        sessao.rollback()
        raise
    finally:
        sessao.close()


def init_db(url: str | None = None) -> None:
    """Cria as tabelas (dev/seed). Em produção usar Alembic."""
    Base.metadata.create_all(bind=get_engine(url))
