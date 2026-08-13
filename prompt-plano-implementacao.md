# Prompt — Plano de Implementação do TradeFlow

> Copie o texto abaixo e cole em um assistente de IA (ChatGPT, Claude, Gemini, Copilot) para gerar o plano de implementação do projeto descrito em `tradeflow.md`.

---

Você é um **engenheiro de software sênior** e **arquiteto de soluções** especializado em sistemas de IA Generativa (LLMs, RAG e agentes), Ciência de Dados e aplicações web em Python. Atue também como **reviewer técnico crítico**: além de propor soluções, você deve apontar riscos, trade-offs e alternativas.

**Contexto do projeto:** o documento `tradeflow.md` descreve o **TradeFlow** — um agente autônomo para análise de documentos de importação (Bill of Lading, Commercial Invoice, Packing List e DI), que extrai dados não estruturados, classifica o código NCM via RAG, prevê prazos de desembaraço e expõe os dados via dashboard e banco SQL.

**Sua tarefa:** crie um **plano de implementação completo, detalhado e acionável** para esse projeto, organizado em fases incrementais, com entregáveis, dependências, critérios de aceitação e estimativa de esforço.

## Requisitos obrigatórios do plano

### 1. Boas práticas de engenharia de software
- Estruture o código em **módulos coesos e desacoplados** (separação de responsabilidades, camadas de domínio/aplicação/infraestrutura).
- Aplique **design patterns** apropriados e justifique cada um: Repository, Service, Factory, Strategy, Adapter, Dependency Injection, Chain of Responsibility (para o pipeline de agentes), Observer, entre outros.
- Aplique **princípios SOLID, DRY, KISS e YAGNI** — sem over-engineering.
- Defina a **estrutura de pastas** do repositório e o papel de cada arquivo.

#### Modularidade (obrigatória)
- Projete o sistema em **módulos coesos e desacoplados**, respeitando as fronteiras naturais de domínio do TradeFlow: extração, classificação NCM, predição, persistência, orquestração e UI.
- Cada módulo deve ter **responsabilidade única**; o módulo de agentes deve apenas **orquestrar** os demais, sem conter a lógica em si.
- Garanta que cada módulo possa ser **testado, reutilizado e substituído isoladamente** (ex.: trocar ChromaDB por Pinecone, ou SQLite por PostgreSQL, sem afetar o resto).
- Evite **dependência circular** entre módulos (ex.: a UI não deve importar detalhes internos dos agentes).
- Use a seguinte estrutura de referência como ponto de partida e **justifique qualquer desvio**:

```
tradeflow/
├── extraction/        # leitura de PDF + extração de campos estruturados
├── ncm/               # RAG + classificação NCM (embeddings, vector store)
├── prediction/        # modelo preditivo + treino/avaliação
├── agents/            # orquestração (CrewAI/LangChain) — só coordena os demais
├── storage/           # repositórios SQL e banco vetorial
├── api/               # REST API (FastAPI/Flask)
├── ui/                # interface Streamlit
├── config/            # configuração e segredos (variáveis de ambiente)
├── utils/             # logging, validação, helpers
├── tests/             # testes unitários, de integração e e2e
└── README.md
```

- **Equilíbrio:** modularidade não é sinônimo de dezenas de pacotes abstratos. Para um projeto de estágio, uma divisão por camadas/responsabilidade é suficiente — evite abstrações prematuras.

### 2. Anti-patterns a evitar
- Liste explicitamente os anti-patterns que **não devem** aparecer no projeto e como evitá-los, por exemplo:
  - God Class / God Module e código monolítico.
  - Código duplicado e funções com múltiplas responsabilidades.
  - *Magic numbers/strings* e lógica de negócio espalhada na UI.
  - Variáveis globais e estado implícito compartilhado.
  - Tratamento de erros com `except: pass` silencioso ou captura excessivamente ampla.
  - Over-engineering (abstrações prematuras) e premature optimization.
  - Dependência circular entre módulos.

### 3. Performance
- Estratégias de **otimização** para cada camada:
  - Extração de PDFs: processamento em lote, paralelismo/async, lazy loading.
  - RAG: chunking adequado, embeddings em cache, índices de busca, reuso de conexões.
  - Chamadas a LLMs: cache de respostas, redução de tokens, batching, timeout e retry com backoff.
  - Banco de dados: índices, queries eficientes, pool de conexões, paginação.
  - Interface: carregamento assíncrono e feedback de progresso.
- Indique **onde medir** antes de otimizar (profiling, métricas de latência e custo).

### 4. Segurança
- **Segredos e credenciais:** nunca hardcoded; uso de variáveis de ambiente e cofre de segredos.
- **Segurança em LLMs:** mitigação de prompt injection, validação/sanitização da saída do modelo, delimitação clara de dados vs. instruções.
- **Upload de arquivos:** validação de tipo/tamanho, sanitização de nome, proteção contra path traversal e malware.
- **APIs:** autenticação/autorização, rate limiting, validação de entrada, proteção contra SQL injection e XSS.
- **Dados:** conformidade com a **LGPD** (dados de importação podem conter dados pessoais/sensíveis), minimização de dados, mascaramento/anonymização, logs sem PII.
- **Dependências:** análise de vulnerabilidades e versionamento pinado.

### 5. Confiabilidade e observabilidade
- Tratamento de erros e **retries idempotentes** (especialmente em chamadas a LLMs e APIs externas).
- **Logging estruturado**, tracing das chamadas de IA e métricas (latência, custo por token, taxa de erro).
- Estratégia de **fallback** quando o LLM falha ou retorna formato inválido (validação de JSON/schema).
- **Versionamento de prompts** e **avaliação de qualidade do RAG** (métricas como precisão/recall, avaliação com dataset de referência).

### 6. Qualidade de código e testes
- **Type hints**, docstrings e comentários relevantes (sem comentários óbvios).
- Estratégia de **testes**: unitários, de integração e end-to-end; como **mockar chamadas a LLMs e embeddings** para testes rápidos e determinísticos.
- Ferramentas de qualidade: linting, formatação, análise estática.

### 7. MLOps (modelo preditivo)
- Versionamento de dados e modelo, split treino/validação/teste, tratamento de vazamento de dados (*data leakage*).
- Métricas de avaliação (R², RMSE, MAE), validação cruzada e monitoramento de drift.
- Como empacotar o modelo e expor a previsão como serviço.

### 8. Infraestrutura, CI/CD e custos
- Gerenciamento de dependências (`pyproject.toml` + `uv`/venv).
- **CI/CD**: lint, testes e build automatizados.
- Estratégia de **contenção de custos** com LLMs (escolha de modelo, cache, limite de tokens).
- Configuração por ambiente (dev, staging, prod).

## Formato da resposta esperada

1. **Visão geral** da arquitetura e fluxo de dados (com diagrama em Mermaid).
2. **Estrutura de pastas** proposta com a responsabilidade de cada módulo.
3. **Fases de implementação** (numeradas), cada uma com:
   - Objetivo e escopo;
   - Tarefas concretas e detalhadas;
   - Tecnologias e padrões utilizados;
   - Critérios de aceitação mensuráveis;
   - Dependências entre fases.
4. **Matriz de riscos** (risco, impacto, mitigação).
5. **Checklist de boas práticas** aplicado a cada fase.

Seja **específico, técnico e prático**. Não descreva apenas conceitos; diga **o quê, como e por quê** implementar, sempre ligado ao contexto do TradeFlow.
