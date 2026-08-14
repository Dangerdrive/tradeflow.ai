"""Testes do client LLM (utils/llm.py) — com chat fake, sem rede."""

import time

import pytest

from extraction.schemas import InvoiceData
from utils.llm import LlmClient, LlmJsonValidationError, _extrair_json, _parse_e_valida


class _Resposta:
    def __init__(self, content: str) -> None:
        self.content = content


class _ChatFake:
    """Chat fake que devolve respostas programadas ou levanta exceções."""

    def __init__(self, respostas=None, falhas=0, **kwargs) -> None:
        self.respostas = list(respostas or [])
        self.falhas = falhas
        self.chamadas: list[str] = []
        self._i = 0

    def invoke(self, prompt: str) -> _Resposta:
        self.chamadas.append(prompt)
        if self.falhas > 0:
            self.falhas -= 1
            raise ConnectionError("rede indisponível")
        if self._i < len(self.respostas):
            resp = self.respostas[self._i]
            self._i += 1
            return _Resposta(resp)
        return _Resposta(
            '{"numero_fatura": "INV-X", "fornecedor": "ACME", '
            '"valor_total_usd": 1, "incoterm": "FOB"}'
        )


def _cliente(chat: _ChatFake, **kw) -> LlmClient:
    return LlmClient(api_key="sk-test", chat_cls=lambda **_: chat, **kw)


def test_generate_text_retorna_conteudo() -> None:
    chat = _ChatFake(["olá"])
    c = _cliente(chat)
    assert c.generate_text("oi") == "olá"


def test_generate_text_retry_com_backoff() -> None:
    chat = _ChatFake(["ok"], falhas=2)
    c = _cliente(chat, backoff_base_s=0.01)
    inicio = time.monotonic()
    assert c.generate_text("oi") == "ok"
    assert time.monotonic() - inicio < 1.0  # backoff curto
    assert len(chat.chamadas) == 3  # 2 falhas + 1 sucesso


def test_generate_text_esgota_retries_e_levanta() -> None:
    chat = _ChatFake(["ok"], falhas=10)
    c = _cliente(chat, max_retries=2, backoff_base_s=0.0)
    with pytest.raises(Exception) as exc:
        c.generate_text("oi")
    assert "LLM falhou" in str(exc.value)
    assert len(chat.chamadas) == 3  # max_retries + 1


def test_generate_structured_valida_contra_schema() -> None:
    chat = _ChatFake(
        [
            '{"numero_fatura": "INV-1", "fornecedor": "ACME", '
            '"valor_total_usd": 10, "incoterm": "FOB"}'
        ]
    )
    c = _cliente(chat)
    dados = c.generate_structured("prompt", InvoiceData)
    assert isinstance(dados, InvoiceData)
    assert dados.numero_fatura == "INV-1"


def test_generate_structured_json_dentro_de_markdown() -> None:
    chat = _ChatFake(
        [
            'Aqui está:\n```json\n{"numero_fatura": "INV-2", '
            '"fornecedor": "Beta", "valor_total_usd": 5, "incoterm": "CIF"}\n```'
        ]
    )
    c = _cliente(chat)
    dados = c.generate_structured("prompt", InvoiceData)
    assert dados.fornecedor == "Beta"


def test_extrair_json_de_texto_livre() -> None:
    assert _extrair_json("texto {a: 1} fim") == "{a: 1}"
    assert _extrair_json('```json\n{"x": 1}\n```') == '{"x": 1}'


def test_parse_e_valida_json_invalido_levanta() -> None:
    with pytest.raises(LlmJsonValidationError):
        _parse_e_valida("isto não é json", InvoiceData)
