"""Teste de smoke da Fase 0 — valida que config e logging carregam."""

import logging

from config.settings import Settings, get_settings
from utils.logging import setup_logging


def test_settings_carrega_com_defaults() -> None:
    settings = get_settings()
    assert isinstance(settings, Settings)
    assert settings.app_name == "TradeFlow"
    assert settings.openai_model == "gpt-4o-mini"
    # Sem .env, a API key deve ficar vazia (nunca um valor real).
    assert settings.openai_api_key == ""


def test_settings_aceita_override_por_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "TradeFlow-Test")
    # get_settings é cacheado; recriar a partir de env para o teste.
    settings = Settings()
    assert settings.app_name == "TradeFlow-Test"


def test_logging_estruturado_inicializa() -> None:
    setup_logging("INFO")
    logger = logging.getLogger("tradeflow")
    assert logger.isEnabledFor(logging.INFO)
