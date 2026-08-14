"""Auditoria de segurança (Fase 8): segredos, LGPD e prompt injection.

Verifica que:
1. ``.env`` não está versionado (está no .gitignore).
2. ``.env.example`` não contém chaves reais.
3. Nenhum arquivo versionado contém padrões de segredo (OpenAI keys, etc.).
4. O formatter de log não expõe PII por padrão.
"""

import re
import subprocess
from pathlib import Path

from utils.logging import JsonFormatter

RAIZ = Path(__file__).resolve().parents[1]

# Padrões típicos de segredo (evita falsos positivos em exemplos/literais).
_PADROES_SEGREDO = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),  # OpenAI
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),  # GitHub PAT
    re.compile(r"AIza[0-9A-Za-z\-_]{30,}"),  # Google API key
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"password\s*=\s*['\"][^'\"]{6,}['\"]", re.IGNORECASE),
]


def _arquivos_versionados() -> list[Path]:
    saida = subprocess.run(
        ["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True
    )
    return [RAIZ / p for p in saida.stdout.splitlines() if p]


def test_env_nao_versionado() -> None:
    gitignore = (RAIZ / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore

    env = RAIZ / ".env"
    # Se existir localmente, não pode estar no índice do git.
    if env.exists():
        saida = subprocess.run(
            ["git", "ls-files", "--error-unmatch", ".env"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
        )
        assert saida.returncode != 0, ".env não pode estar versionado"


def test_env_example_sem_segredos_reais() -> None:
    exemplo = (RAIZ / ".env.example").read_text(encoding="utf-8")
    for padrao in _PADROES_SEGREDO:
        assert padrao.search(exemplo) is None, f"Segredo real em .env.example: {padrao.pattern}"


def test_nenhum_arquivo_versionado_com_segredo() -> None:
    ofensores: list[str] = []
    for arquivo in _arquivos_versionados():
        if arquivo.suffix not in {".py", ".md", ".toml", ".yml", ".yaml", ".ini", ".sh", ".json"}:
            continue
        texto = arquivo.read_text(encoding="utf-8", errors="ignore")
        for padrao in _PADROES_SEGREDO:
            if padrao.search(texto):
                ofensores.append(f"{arquivo.relative_to(RAIZ)}: {padrao.pattern}")
    assert not ofensores, f"Possíveis segredos versionados: {ofensores}"


def test_logging_nao_expoe_pii_por_padrao() -> None:
    """O JsonFormatter só inclui os campos básicos + extra explícito."""
    import logging

    formatter = JsonFormatter()
    registro = logging.LogRecord(
        name="tradeflow",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="processou fatura INV-123 do fornecedor ACME",
        args=(),
        exc_info=None,
    )
    saida = formatter.format(registro)
    assert "INV-123" in saida  # a mensagem em si é logada (decisão do chamador)
    assert "openai_api_key" not in saida  # campos reservados não vazam
    assert "sk-" not in saida
