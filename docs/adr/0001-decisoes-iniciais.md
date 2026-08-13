# ADR 0001 — Decisões iniciais de arquitetura

- **Status:** Aceito
- **Data:** 2026-08-13

## Contexto

O TradeFlow precisa orquestrar agentes de IA, extrair dados de PDFs, usar RAG
para classificação NCM, prever prazos e expor os resultados. As decisões abaixo
definem a base técnica (Fase 0).

## Decisões

### 1. CrewAI sobre LangChain puro para orquestração
- **Decisão:** usar CrewAI para definir papéis/agentes/tarefas de forma
  declarativa, com LangChain como base para tools e integrações.
- **Consequência:** orquestração mais legível e evolutiva; custo de aprender a
  API do CrewAI.

### 2. ChromaDB (local) como banco vetorial
- **Decisão:** começar com ChromaDB local, mantendo uma interface `VectorStore`
  para permitir troca futura por Pinecone.
- **Consequência:** simplicidade em dev; migração futura isolada no módulo `ncm`.

### 3. SQLite em dev, PostgreSQL em prod
- **Decisão:** `DATABASE_URL` via ambiente; SQLite por padrão, PostgreSQL
  quando configurado. SQLAlchemy abstrai o dialeto.
- **Consequência:** troca de banco sem alterar código (apenas `.env`).

### 4. Execução assíncrona do pipeline
- **Decisão:** o pipeline roda em background (`jobs/`), com o registro passando
  por status `pendente → processando → concluído/erro`.
- **Consequência:** evita timeouts em chamadas síncronas; exige polling de status.

### 5. Logging estruturado (JSON) + correlation ID
- **Decisão:** logs em JSON com `correlation_id` para rastreabilidade, sem PII.
- **Consequência:** facilita observabilidade; requer disciplina para não logar PII.

## Consequências

- Estrutura de pastas por domínio (`extraction/`, `ncm/`, `prediction/`, ...).
- Configuração centralizada via `pydantic-settings`.
- CI com lint (ruff), formatação (black), testes (pytest) e auditoria (`pip-audit`).
