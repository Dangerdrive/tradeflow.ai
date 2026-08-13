# ⚓ TradeFlow — Agente Autônomo para Análise de Documentos de Importação

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)

Ecosistema de agentes de IA que **recebe** documentos de importação (Bill of Lading, Commercial Invoice, Packing List e DI), **extrai** dados estruturados, **classifica** o código NCM via RAG, **prevê** prazos de desembaraço e **disponibiliza** tudo em banco SQL e dashboard.

---

## 🎯 O problema

Uma empresa de importação recebe centenas de documentos por dia. Um analista gasta horas extraindo manualmente NCM, peso, valor, fornecedor e incoterms, gerando:

- Erros de digitação
- Atrasos no desembaraço aduaneiro
- Multas por classificação fiscal incorreta

## 💡 A solução

Um pipeline de IA em 5 estágios: **receber → extrair → classificar NCM → prever → persistir e expor**.

```mermaid
flowchart LR
    U[Usuário / Analista] --> UI[Streamlit UI]
    UI --> API[REST API - FastAPI]
    API --> ORQ[Orquestrador - CrewAI]
    ORQ --> EXT[Agente Extrator]
    ORQ --> NCM[Agente Classificador NCM]
    ORQ --> PRED[Agente Preditivo]
    EXT --> PDF[pdfplumber / OCR]
    EXT --> LLM[LLM GPT-4o-mini]
    NCM --> VS[(ChromaDB - Vector Store)]
    NCM --> LLM
    PRED --> ML[Modelo Scikit-learn]
    ORQ --> DB[(PostgreSQL)]
    API --> DB
    UI --> DB
```

---

## ✨ Funcionalidades

- 📄 Upload de PDFs (com suporte a documentos escaneados via OCR)
- 🤖 Extração estruturada de campos (fatura, fornecedor, valor, peso, incoterm, volumes) com validação de schema
- 🔍 Classificação automática de NCM via RAG (sugere os 3 códigos mais prováveis)
- 📈 Previsão de prazo de desembaraço com modelo de regressão
- 🗄️ Persistência em banco relacional (PostgreSQL/SQLite)
- 🌐 REST API para integração com sistemas legados
- 🖥️ Dashboard Streamlit com revisão humana
- 🔒 Segurança: segredos em ambiente, proteção contra prompt injection, conformidade LGPD

---

## 🧰 Stack tecnológica

| Componente | Tecnologia |
| :--- | :--- |
| Orquestração de agentes | LangChain + CrewAI |
| Extração de dados | pdfplumber / PyPDF2 / pytesseract + OpenAI GPT-4o-mini |
| Banco vetorial (RAG) | ChromaDB |
| Banco relacional | PostgreSQL (dev: SQLite) |
| Análise preditiva | Pandas + Scikit-learn |
| API | FastAPI |
| Interface | Streamlit |
| Qualidade | ruff, black, pytest |
| Versionamento de dados | DVC |

---

## 📁 Estrutura do projeto

```
tradeflow/
├── extraction/            # leitura de PDF + extração de campos estruturados
├── ncm/                   # RAG + classificação NCM
├── prediction/            # modelo preditivo + treino/avaliação
├── agents/                # orquestração (CrewAI) — só coordena
├── storage/               # repositórios SQL e banco vetorial
├── api/                   # REST API (FastAPI)
├── ui/                    # interface Streamlit
├── jobs/                  # processamento assíncrono (fila/workers)
├── config/                # configuração e segredos (variáveis de ambiente)
├── utils/                 # logging, validação, helpers, client LLM
├── tests/                 # testes unitários, de integração e e2e
├── data/                  # datasets (raw/ e processed/ — versionados com DVC)
├── models/                # artefatos de modelo serializados (joblib)
├── docs/adr/              # Architecture Decision Records
├── notebooks/             # EDA e experimentos
└── pyproject.toml         # dependências + tooling (uv, ruff, black)
```

---

## 🚀 Pré-requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (gerenciador de dependências)
- Git
- Uma chave da API OpenAI (`OPENAI_API_KEY`)
- (Opcional) PostgreSQL local ou Docker

---

## ⚙️ Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/tradeflow.git
cd tradeflow

# 2. Instale as dependências com uv (cria o .venv automaticamente)
uv sync

# 3. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com sua OPENAI_API_KEY, DATABASE_URL, etc.
```

---

## 🔑 Configuração (`.env`)

| Variável | Descrição | Exemplo |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | Chave da API OpenAI | `sk-...` |
| `OPENAI_MODEL` | Modelo LLM usado na extração | `gpt-4o-mini` |
| `DATABASE_URL` | URL do banco relacional | `postgresql+psycopg2://user:pass@localhost/tradeflow` |
| `CHROMA_PERSIST_DIR` | Diretório do vector store | `./data/chroma` |
| `LOG_LEVEL` | Nível de logging | `INFO` |

> ⚠️ **Nunca** versione o `.env` no Git. Use `.env.example` como referência.

---

## ▶️ Como executar

> Todos os comandos rodam dentro do ambiente do projeto via `uv run`.

### Dashboard (Streamlit)

```bash
uv run streamlit run ui/app.py
```

### API (FastAPI)

```bash
uv run uvicorn api.main:app --reload
```

A documentação interativa fica em `http://localhost:8000/docs`.

### Testes

```bash
uv run pytest
```

### Lint, formatação e auditoria

```bash
uv run ruff check .
uv run black --check .
uv run pip-audit
```

---

## 🌐 Endpoints da API

| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `POST` | `/importacoes/upload` | Recebe um PDF, enfileira o pipeline e retorna `202` com ID |
| `GET` | `/importacoes/{id}/status` | Consulta o status do processamento |
| `GET` | `/importacoes` | Lista as importações |
| `GET` | `/importacoes/{id}` | Retorna os detalhes de uma importação |

**Exemplo de resposta do upload:**

```json
{
  "id": 42,
  "status": "pendente_revisao",
  "numero_fatura": "INV-2026-0842",
  "ncm_sugerido": "8528.72.00",
  "prazo_estimado_dias": 9
}
```

---

## 🤖 O pipeline de agentes

1. **Agente Extrator** — lê o PDF (texto ou OCR) e extrai os campos com Few-Shot + Chain-of-Thought, validando o resultado com Pydantic. Em caso de falha do LLM, um **fallback determinístico por regex** é acionado.
2. **Agente Classificador Fiscal** — usa RAG sobre a Tabela TIPI (NCM) para sugerir os 3 códigos mais prováveis.
3. **Agente Preditivo** — aplica o modelo treinado para estimar o prazo de desembaraço.

O resultado é persistido com status `pendente` para **revisão humana** — essencial num domínio fiscal onde erro gera multa.

---

## 🔒 Segurança e privacidade

- Segredos via variáveis de ambiente (nunca hardcoded).
- Mitigação de **prompt injection**: delimitadores explícitos entre dados e instruções, sanitização de entrada e validação de saída.
- Validação de upload (tipo, tamanho, nome sanitizado).
- Conformidade com a **LGPD**: minimização de dados, logs sem PII e mascaramento de campos sensíveis.
- Análise de vulnerabilidades em dependências (`pip-audit`).

---

## 🗺️ Roadmap

| Fase | Descrição | Status |
| :--- | :--- | :---: |
| 0 | Fundação (estrutura, config, CI) | ⬜ |
| 1 | Extração estruturada + OCR | ⬜ |
| 2 | RAG para classificação NCM | ⬜ |
| 3 | Modelo preditivo | ⬜ |
| 4 | Camada de dados SQL | ⬜ |
| 5 | Orquestração (CrewAI) | ⬜ |
| 6 | API REST | ⬜ |
| 7 | Dashboard Streamlit | ⬜ |
| 8 | Hardening, avaliação e entrega | ⬜ |

O **MVP vertical** (Fases 0 → 1 → 2 → 7) entrega a demo de ponta a ponta para a entrevista.

> Consulte [`plano-implementacao.md`](./plano-implementacao.md) para o plano detalhado com tarefas, critérios de aceitação e riscos.

---

## ⚠️ Limitações (fora do escopo)

- Autenticação JWT/OAuth (usa API key + HTTPS por enquanto).
- Fine-tuning de LLMs próprios.
- Multi-tenancy e escala horizontal.
- Integração real com Siscomex/DUIMP.

---

## 📄 Licença

Distribuído sob a licença **MIT**.

---

Feito com ❤️ para a vaga de estágio na **DUIMPWEB** — foco em dados não estruturados, RAG, agentes e análise preditiva.
