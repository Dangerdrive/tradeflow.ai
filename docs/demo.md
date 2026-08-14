# 🎬 Roteiro da Demo — TradeFlow

> Documento para o vídeo de demonstração da entrevista. Os outputs abaixo são
> **reais** (gerados em 2026-08-14 sem `OPENAI_API_KEY`, usando componentes
> determinísticos: regex + HashEmbedder + modelo treinado).

---

## 1. Objetivo da demo

Mostrar o **MVP vertical de ponta a ponta**: upload de uma Commercial Invoice
(PDF) → extração estruturada → classificação NCM (RAG) → previsão de prazo →
persistência e revisão humana. Tudo em **~1 segundo**, sem custo de LLM.

**Tempo alvo do vídeo:** 3–5 minutos.

---

## 2. Pré-requisitos (rodar antes de gravar)

```bash
bash scripts/setup.sh            # deps + .env + migrations + seed + treino + índice
uv run python scripts/seed_db.py # dados de demonstração (idempotente)
```

> ⚠️ Para a demo **sem chave OpenAI**: o sistema usa fallback regex +
> HashEmbedder. Com `OPENAI_API_KEY` no `.env`, usa LLM + embeddings semânticos
> (qualidade maior, principalmente nos itens e no NCM).

---

## 3. Roteiro passo a passo

### Passo 0 — Visão da arquitetura (30s, tela fixa)

Mostre o diagrama do README e diga (script):

> "Recebemos PDFs de importação. Um **ecossistema de agentes** extrai os dados,
> classifica o **NCM** via RAG sobre a Tabela TIPI, prevê o **prazo de
> desembaraço** e persiste tudo em banco para **revisão humana** — porque no
> domínio fiscal um erro gera multa."

### Passo 1 — Processar uma fatura pelo pipeline (1min)

Suba o **Streamlit** (`uv run streamlit run ui/app.py`), na seção
**"1. Processar uma fatura"** envie `data/raw/samples/invoice_002.pdf`
(fatura em português, com acentos — mostra robustez do parser).

Resultado real esperado:

| Campo | Valor |
| :--- | :--- |
| Fatura | `FT-2026-1122` |
| Fornecedor | `Logística BR Import` |
| Valor total (USD) | `8.900,00` |
| Peso bruto | `150 kg` |
| Incoterm | `CIF` |
| Volumes | `5` |
| NCM sugerido | `9405.40.10` (Lâmpada LED) |
| Prazo estimado | `7 dias` |
| Itens extraídos | `Lampada LED 9W` (4.450), `Cabo USB-C 2m` (4.450) |
| Latência total | **~0,15s** (sem LLM) |

> **Dica de narrativa:** destaque que o NCM `9405.40.10` veio do **RAG** (busca
> de similaridade na Tabela TIPI) e que a extração **não usou LLM** — é o
> fallback determinístico rodando em frações de segundo.

### Passo 2 — Fluxo via API (1min) — opcional, bom para entrevista técnica

Mostre a API (`uv run uvicorn api.main:app --reload`, Swagger em `/docs`) ou
execute os comandos:

```bash
# 1) upload -> 202 (processamento assíncrono)
curl -X POST http://localhost:8000/importacoes/upload -F "arquivo=@data/raw/samples/invoice_002.pdf"
# resposta: {"importacao_id": 4, "status": "pendente", ...}

# 2) consultar status
curl http://localhost:8000/importacoes/4/status
# resposta: {"importacao_id": 4, "status": "concluido", ...}

# 3) detalhe completo
curl http://localhost:8000/importacoes/4
```

**Saída real (fatura de café, `FT-2026-2055`):**

```json
UPLOAD: 202 {"importacao_id": 4, "status": "pendente", "mensagem": "Upload aceito — processamento em andamento."}
STATUS: {"importacao_id": 4, "status": "concluido", "observacao": "upload=invoice_cafe.pdf"}
DETALHE: {
  "numero_fatura": "FT-2026-2055",
  "fornecedor": "Indústrias Andinas",
  "valor_total_usd": 5678.9,
  "peso_bruto_kg": 210.0,
  "incoterm": "EXW",
  "volumes": 8,
  "ncm_sugerido": "0901.22.00",
  "prazo_estimado_dias": 18,
  "status": "concluido"
}
ITENS: [["Café torrado 1kg", 2839.45], ["Café torrado 500g", 2839.45]]
```

> **Dica de narrativa:** "o upload retorna **202 Accepted** e o processamento
> roda em background (worker), com o registro passando por
> `pendente → processando → concluído`. O status é consultável."

### Passo 3 — Revisão humana (30s)

Na mesma UI, seção **"3. Revisão humana"**: selecione a importação e marque
como **revisado** ou **corrigido** (com observação). Mostre a linha atualizada
na tabela.

> **Dica de narrativa:** "a revisão humana é essencial — no comércio exterior,
> um NCM errado gera multa. O sistema suporta o ciclo
> `pendente → revisado/corrigido` e guarda o JSON bruto (`payload_bruto`) para
> auditoria."

### Passo 4 — Avaliação de qualidade (30s)

Mostre que a precisão é medida, não assumida:

```bash
uv run python scripts/evaluate_extraction.py   # extração: 100% (meta 90%)
uv run python scripts/evaluate_ncm.py          # RAG: precision@3 93% (meta 85%)
uv run python scripts/estimar_custo_llm.py     # custo: ~US$ 0,23 / 1.000 docs
```

---

## 4. Checklist de gravação

- [ ] `bash scripts/setup.sh` rodado (banco + seed + modelo treinado)
- [ ] Streamlit aberto em `http://localhost:8501`
- [ ] PDF `data/raw/samples/invoice_002.pdf` pronto para upload
- [ ] API opcional rodando (`uvicorn api.main:app --reload`)
- [ ] Ter à mão: diagrama de arquitetura, `docs/evaluation/relatorio-metricas.md`
- [ ] Evitar mostrar dados sensíveis; usar os PDFs sintéticos do golden dataset

---

## 5. Perguntas que a demo já responde

- **Extração funciona sem LLM?** Sim — fallback regex determinístico (100% no golden).
- **Como o NCM é sugerido?** RAG de similaridade na Tabela TIPI (ChromaDB/InMemory).
- **E se o LLM falhar?** Retry com backoff + fallback regex; nunca quebra o pipeline.
- **E se a mesma fatura for enviada 2x?** Idempotência por `(numero_fatura, fornecedor)`.
- **Custo?** ~US$ 0,23 / 1.000 documentos (gpt-4o-mini, com cache por prompt).
