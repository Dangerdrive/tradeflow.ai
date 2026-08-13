# Baseline — Fase U0 (pré-upgrade)

- **Data (UTC):** 2026-08-13
- **Projeto:** TradeFlow (tradeflow.ai)
- **Objetivo:** registrar o estado de referência antes do upgrade amplo de dependências.

## Ambiente

| Item | Valor |
| :--- | :--- |
| Gerenciador | uv 0.12.3 |
| Python (venv) | CPython 3.12.13 |
| `requires-python` | >=3.11 |

## Resultados de referência

| Verificação | Resultado |
| :--- | :--- |
| `uv run pytest` | ✅ 3 passed (0.17s) |
| `uv run ruff check .` | ✅ All checks passed |
| `uv run black --check .` | ✅ 14 files unchanged |
| `uv pip check` | ✅ 220 packages — all compatible |
| `uv run pip-audit` | ❌ **104 vulnerabilidades em 19 pacotes** |

## Pacotes com vulnerabilidades (resumo)

Log completo em [`baseline-u0.log`](./baseline-u0.log). Destaques:

- `pypdf` / `PyPDF2` / `pdfminer-six` / `pillow` — cadeia de processamento de PDF (crítico para o TradeFlow)
- `langchain`, `langchain-core`, `langchain-openai`, `langchain-community`, `langsmith`, `mem0ai`
- `streamlit`, `starlette`, `python-multipart` — camada web/API
- `black`, `pytest`, `python-dotenv` — tooling

## Observações

- As vulnerabilidades decorrem de **versões pinadas de 2024** (data atual: 2026).
- Este baseline será usado como comparação na fase **U4** para comprovar a eliminação das CVEs e a ausência de regressão.

## Próximos passos (não executados nesta fase)

- Criar branch `chore/upgrade-deps` + tag `pre-upgrade`.
- Fase U1: atualizar dev tools (ruff, black, pytest, pip-audit).
