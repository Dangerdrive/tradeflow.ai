# 🎤 Preparação para a Entrevista — TradeFlow

> Resumo executivo, decisões técnicas e respostas às perguntas difíceis.
> Use como roteiro mental; **fale com as suas palavras**.

---

## 1. Elevator pitch (30s)

> "Construí o **TradeFlow**: um ecossistema de agentes de IA que automatiza a
> análise de documentos de importação. Ele **extrai** os dados de uma Commercial
> Invoice (PDF), **classifica o NCM** via RAG sobre a Tabela TIPI, **prevê o
> prazo de desembaraço** com um modelo de regressão e **persiste** tudo em banco
> para revisão humana. O diferencial é a robustez: fallback determinístico quando
> o LLM falha, idempotência, validação de schema e avaliação de qualidade medida
> (100% de precisão na extração e 93% de precision@3 no NCM)."

---

## 2. Arquitetura (em 5 camadas)

```
UI (Streamlit) → API (FastAPI) → Orquestrador (pipeline/worker) → Domínio (extraction, ncm, prediction) → Infra (storage SQL + Chroma)
```

Princípios seguidos:
- **Camadas desacopladas** — o domínio não conhece UI/API; o orquestrador só coordena.
- **Interfaces estáveis** — `Embedder`, `VectorStore`, `Extrator` são protocolos
  (Strategy): trocar ChromaDB→Pinecone ou regex→LLM não altera o resto.
- **Thin UI** — nenhuma regra de negócio em `ui/app.py`.
- **Testável sem custo** — LLM, embeddings e modelo são injetáveis/fakes.

---

## 3. Decisões técnicas (por quê)

| Decisão | Por quê |
| :--- | :--- |
| **Fallback regex + LLM** | LLM falha/inventa; o regex garante extração determinística e gratuita (100% no golden). |
| **HashEmbedder sem chave** | Embeddings OpenAI custam tokens; um embedder lexical determinístico permite demo/CI sem `OPENAI_API_KEY`. |
| **Pipeline determinístico** | Orquestrar módulos de domínio diretamente (em vez de `crew.kickoff`) torna o fluxo testável e barato; CrewAI fica como showcase. |
| **Idempotência** | `UNIQUE(numero_fatura, fornecedor)` — reprocessar não duplica; o registro canônico é atualizado. |
| **Split antes do pré-processamento** | Evita *data leakage*: o `FeatureTransformer` é fit apenas no treino e reutilizado na inferência. |
| **uv + pyproject.toml** | Lock determinístico (`uv.lock`), rollback garantido, ambientes reprodutíveis. |
| **SQLite dev / PostgreSQL prod** | Trocar o banco muda só a `DATABASE_URL` (SQLAlchemy + Alembic). |

---

## 4. Perguntas difíceis (e respostas)

### "Por que o hash embedder errou o NCM de alguns produtos?"
**Contexto honesto:** com HashEmbedder (sem custo), precision@3 é 93%; os erros
são lexicais (ex.: "monitor de computador" e "steel bearing" — sinônimos que o
embedding lexical não captura). **Com OpenAIEmbeddings** a precisão sobe. A
arquitetura permite trocar o embedder sem tocar no classificador (Strategy).

### "Você conhece a vulnerabilidade do ChromaDB? Por que não atualizou?"
**PYSEC-2026-311** — injeção de código pré-autenticação que afeta **todas as
versões 1.x** do ChromaDB; **não há versão corrigida publicada**. O upgrade
(crewai/chromadb) não resolve. **Mitigação:** Chroma bindado a localhost e
`trustremotecode=false`. Está documentado e reavaliado a cada upgrade.

### "Como evitou data leakage no modelo preditivo?"
`train_test_split` **antes** de qualquer transformação; um único
`FeatureTransformer` (fit no treino) é usado na inferência; o teste
`test_preprocess_consistente_treino_inferencia` prova a mesma saída.

### "Como controlou o custo de LLM?"
Cache por prompt (sha256) em `utils/llm.py`, `max_tokens` limitado, fallback
regex quando o LLM falha, modelo configurável (`gpt-4o-mini`). Estimativa real:
**~US$ 0,23 / 1.000 documentos** (`scripts/estimar_custo_llm.py`).

### "E prompt injection vindo do PDF?"
O prompt de extração usa **delimitadores explícitos** (dados vs. instruções) e
instrui a ignorar instruções dentro do documento; a saída é **validada contra
um schema Pydantic** antes de ser usada; nada no conteúdo do PDF é executado.

### "Por que 202 Accepted em vez de processamento síncrono?"
O pipeline pode demorar (LLM/OCR). O upload devolve `202` com ID e o **worker em
background** atualiza o status `pendente → processando → concluído/erro`,
consultável via `GET /importacoes/{id}/status`. Em produção: Celery/Redis.

### "Como sabe que a extração está correta?"
**Golden dataset**: 10 PDFs anotados (`data/golden/`) com ground truth. A
avaliação mede a precisão por campo (100% — meta 90%). Além disso, `payload_bruto`
guarda o JSON original para auditoria e há **revisão humana** no fluxo.

### "Qual a diferença entre o pipeline e o CrewAI?"
O pipeline (produção) orquestra os módulos de domínio — determinístico, testável,
sem custo. O `agents/crew.py` define os **mesmos papéis em CrewAI** (Extrator,
Classificador Fiscal, Analista Preditivo) como alternativa para demonstrar o
framework de agentes.

### "Se tivesse mais tempo, o que faria?"
1. **Tabela TIPI real** (baixar a oficial) em vez da amostra de 59 códigos.
2. **PostgreSQL** de verdade (validei só em SQLite).
3. **Fila de produção** (Celery + Redis) e retry com backoff externo.
4. **Monitoramento de drift em produção** (o módulo existe em `prediction/drift.py`).
5. **JWT/OAuth** e multi-tenancy.

---

## 5. Números para citar

| Métrica | Valor | Meta |
| :--- | :---: | :---: |
| Precisão extração (golden) | **100%** | ≥ 90% |
| RAG NCM precision@3 | **93%** | ≥ 85% |
| Modelo preditivo R² | **0.952** | > 0.8 |
| Custo LLM (1.000 docs/mês) | **~US$ 0,23** | — |
| Testes | **~87** | CI verde |
| Latência pipeline (sem LLM) | **~0,15s** | — |

---

## 6. Docs para levar (links)

- `docs/demo.md` — roteiro do vídeo
- `docs/evaluation/relatorio-metricas.md` — relatório de avaliação
- `plano-implementacao.md` — plano completo + status
- `docs/adr/0001-decisoes-iniciais.md` — decisões de arquitetura
- `README.md` — visão geral e setup
