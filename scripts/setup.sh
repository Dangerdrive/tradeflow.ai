#!/usr/bin/env bash
# setup.sh — prepara o ambiente TradeFlow de ponta a ponta.
# Uso: bash scripts/setup.sh   (ou ./scripts/setup.sh após chmod +x)
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "erro: 'uv' não encontrado. Instale: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

echo "==> 1/6 Instalando dependências (uv sync)"
uv sync

echo "==> 2/6 Criando .env a partir de .env.example (se não existir)"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "    .env criado — edite com sua OPENAI_API_KEY (opcional na demo)."
fi

echo "==> 3/6 Criando tabelas do banco (Alembic)"
uv run alembic upgrade head

echo "==> 4/6 Seed de dados de demonstração"
uv run python scripts/seed_db.py

echo "==> 5/6 Treinando modelo preditivo de prazo"
uv run python -m prediction.train

echo "==> 6/6 Índice NCM (ChromaDB)"
uv run python scripts/build_ncm_index.py || \
  echo "    aviso: sem OPENAI_API_KEY — a demo usará o embedder hash em memória."

echo ""
echo "Setup concluído! Próximos passos:"
echo "  uv run streamlit run ui/app.py           # dashboard"
echo "  uv run uvicorn api.main:app --reload     # API (docs em /docs)"
echo "  uv run pytest                            # testes"
