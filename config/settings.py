"""Configuração centralizada do TradeFlow.

Carrega variáveis de ambiente via ``pydantic-settings`` a partir de um
arquivo ``.env`` (ou do ambiente). Nenhum segredo é declarado aqui —
apenas referenciado como campo.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações do TradeFlow (lidas de .env / ambiente)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- OpenAI ---
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # --- Banco de dados relacional ---
    database_url: str = "sqlite:///./data/tradeflow.db"

    # --- Banco vetorial (ChromaDB) ---
    chroma_persist_dir: str = "./data/chroma"

    # --- Aplicação ---
    app_name: str = "TradeFlow"
    log_level: str = "INFO"
    max_upload_size_mb: int = 25
    allowed_document_extensions: tuple[str, ...] = (".pdf",)


@lru_cache
def get_settings() -> Settings:
    """Retorna a instância única de Settings (cache para evitar re-leitura)."""
    return Settings()
