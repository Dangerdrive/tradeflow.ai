"""Client LLM com timeout, retry com backoff exponencial e validação de saída.

Usa o client síncrono do pacote ``openai`` (v2.x). A extração retorna JSON
que é validado contra um schema Pydantic — se inválido, tenta um reparo
(pedir JSON válido novamente) antes de propagar o erro.

Contenção de custos: modelo configurável via ``Settings.openai_model`` e
``max_tokens`` limitado por chamada.
"""

from __future__ import annotations

import json
import logging
import time
from typing import TypeVar, get_args, get_origin

from pydantic import BaseModel, ValidationError

logger = logging.getLogger("tradeflow.utils.llm")

T = TypeVar("T", bound=BaseModel)

# Configuração de robustez.
_DEFAULT_TIMEOUT_S = 30.0
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BACKOFF_BASE_S = 1.0


class LlmError(RuntimeError):
    """Erro genérico de chamada ao LLM (após esgotar retries)."""


class LlmJsonValidationError(LlmError):
    """O LLM retornou texto que não pôde ser validado como JSON/schema."""


class LlmClient:
    """Wrapper fino sobre o client da OpenAI com retry/backoff.

    Para testes, injete ``chat_cls`` (a classe de chat) — os testes usam um
    fake que não faz chamadas de rede.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        *,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        timeout_s: float = _DEFAULT_TIMEOUT_S,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        backoff_base_s: float = _DEFAULT_BACKOFF_BASE_S,
        chat_cls=None,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.backoff_base_s = backoff_base_s

        if chat_cls is None:
            from langchain_openai import ChatOpenAI

            chat_cls = ChatOpenAI
        self._chat = chat_cls(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout_s,
        )

    # ------------------------------------------------------------------ API

    def generate_text(self, prompt: str) -> str:
        """Chama o LLM com retry/backoff e retorna o texto da resposta."""
        ultimo_erro: Exception | None = None
        for tentativa in range(self.max_retries + 1):
            try:
                resposta = self._chat.invoke(prompt)
                return str(resposta.content)
            except Exception as exc:  # noqa: BLE001 — retry em qualquer falha de rede
                ultimo_erro = exc
                logger.warning(
                    "llm_falha",
                    extra={"tentativa": tentativa + 1, "erro": str(exc)},
                )
                if tentativa < self.max_retries:
                    time.sleep(self.backoff_base_s * (2**tentativa))
        raise LlmError(f"LLM falhou após {self.max_retries + 1} tentativas") from ultimo_erro

    def generate_structured(self, prompt: str, schema: type[T]) -> T:
        """Chama o LLM pedindo JSON e valida contra ``schema``.

        Primeiro tenta o JSON como veio; se a validação falhar, tenta uma
        segunda chamada ("reparo") pedindo apenas o JSON corrigido.
        """
        texto = self.generate_text(prompt)
        try:
            return _parse_e_valida(texto, schema)
        except LlmJsonValidationError as exc:
            logger.info("llm_json_invalido_na_primeira_tentativa", extra={"erro": str(exc)})
            # Reparo: segunda chamada pedindo JSON válido.
            prompt_reparo = (
                "A resposta anterior não era um JSON válido para o schema.\n"
                f"Erro: {exc}\n"
                "Responda APENAS com o JSON corrigido, sem comentários.\n"
                f"JSON: {texto}"
            )
            texto2 = self.generate_text(prompt_reparo)
            return _parse_e_valida(texto2, schema)


# ------------------------------------------------------------------ helpers


def _parse_e_valida(texto: str, schema: type[T]) -> T:
    """Interpreta ``texto`` como JSON e valida contra ``schema``."""
    json_texto = _extrair_json(texto)
    try:
        dados = json.loads(json_texto)
    except json.JSONDecodeError as exc:
        raise LlmJsonValidationError(f"JSON inválido: {exc}") from exc

    # Aceita schema raiz (dict) ou lista de schemas (campo "resultado").
    alvo = schema
    if get_origin(schema) is list:
        alvo = get_args(schema)[0]
        if isinstance(dados, list):
            return schema(dados)  # type: ignore[return-value]
        if isinstance(dados, dict):
            for chave in ("resultado", "resultados", "itens", "data"):
                if isinstance(dados.get(chave), list):
                    return schema(dados[chave])  # type: ignore[return-value]
            raise LlmJsonValidationError("JSON não contém lista para schema list")
    try:
        return alvo.model_validate(dados)
    except ValidationError as exc:
        raise LlmJsonValidationError(f"Falha de validação: {exc}") from exc


def _extrair_json(texto: str) -> str:
    """Extrai o bloco JSON (entre ```json ... ``` ou chaves) de um texto."""
    texto = texto.strip()
    if "```" in texto:
        # Pega o primeiro bloco de código.
        partes = texto.split("```")
        for parte in partes:
            parte = parte.strip()
            if parte.startswith("json"):
                parte = parte[4:].strip()
            if parte.startswith("{") or parte.startswith("["):
                return parte
    # Fallback: recorta entre a primeira { e a última }.
    inicio = texto.find("{")
    fim = texto.rfind("}")
    if inicio != -1 and fim != -1 and fim > inicio:
        return texto[inicio : fim + 1]
    return texto
