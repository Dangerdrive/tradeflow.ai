# Relatório de Avaliação — TradeFlow

> Gerado em 2026-08-14. Medidas obtidas com os scripts de avaliação do projeto
> (`scripts/evaluate_extraction.py`, `scripts/evaluate_ncm.py`,
> `python -m prediction.train`, `scripts/estimar_custo_llm.py`).
> Os valores sem `OPENAI_API_KEY` usam componentes determinísticos
> (regex + HashEmbedder); com chave OpenAI espera-se resultados ≥ estes.

---

## 1. Extração (Fase 1) — golden dataset

**Dataset:** 10 PDFs sintéticos de Commercial Invoice em `data/raw/samples/`,
anotados em `data/golden/golden_annotations.json`.

| Campo | Acerto | Precisão |
| :--- | :---: | :---: |
| numero_fatura | 10/10 | 100% |
| fornecedor | 10/10 | 100% |
| valor_total_usd | 10/10 | 100% |
| peso_bruto_kg | 10/10 | 100% |
| incoterm | 10/10 | 100% |
| volumes | 10/10 | 100% |
| **Documentos com 6/6** | **10/10** | **100%** |

Meta do plano: ≥ 90% dos documentos com 6/6. ✅ **Excedida** (baseline regex).

---

## 2. RAG NCM (Fase 2) — golden dataset

**Dataset:** 30 descrições de produtos anotadas em
`data/golden/golden_ncm.json`, contra a Tabela TIPI de amostra
(`data/tabela_ncm.csv`, 59 códigos).

| Métrica | Valor | Meta |
| :--- | :---: | :---: |
| precision@1 | 73% | — |
| precision@3 | **93%** | ≥ 85% |

✅ Meta atingida com o **HashEmbedder** (determinístico, sem custo). Com
embeddings semânticos (OpenAI) a precision@1 tende a melhorar
(ambiguidades lexicais como "monitor de computador" e "televisor LED").

---

## 3. Modelo preditivo de prazo (Fase 3)

**Dataset:** `data/historico_importacoes.csv` (500 registros sintéticos
determinísticos, seed 42).

| Métrica | Valor |
| :--- | :---: |
| Modelo selecionado | LinearRegression |
| R² (teste) | 0.952 |
| RMSE (teste) | 2.45 dias |
| MAE (teste) | 2.00 dias |

> O dataset é sintético com relação quase linear — o R² alto valida o
> **pipeline** (sem data leakage, split antes do pré-processamento), não a
> qualidade do dado real. Com dados reais, reavaliar e comparar modelos.

---

## 4. Custo estimado de LLM (Fase 8)

Medido no golden dataset (10 PDFs), modelo `gpt-4o-mini`
(US$ 0.15/1M entrada, US$ 0.60/1M saída):

| Item | Valor |
| :--- | :---: |
| Tokens médios de entrada / documento | 919 |
| Tokens médios de saída / documento | 161 |
| Custo / documento | ~US$ 0.00023 |
| Custo mensal (1.000 docs) | ~US$ 0.23 |

**Mitigações ativas:** cache por prompt (`utils/llm.py`), `max_tokens`
limitado, fallback regex quando o LLM falha, modelo escolhido em Settings.

---

## 5. Segurança

- `pip-audit`: **0 vulnerabilidades** (1 exceção documentada: chromadb
  `PYSEC-2026-311` — todas as 1.x afetadas, sem fix; mitigação: Chroma local).
- Scan de segredos: teste `tests/test_seguranca.py` + passo `gitleaks` no CI.
- Prompt injection: delimitadores dados/instruções no prompt de extração.
- LGPD: logging JSON sem PII por padrão.

---

## 6. Como reproduzir

```bash
uv run python scripts/evaluate_extraction.py   # seção 1
uv run python scripts/evaluate_ncm.py          # seção 2
uv run python -m prediction.train              # seção 3
uv run python scripts/estimar_custo_llm.py     # seção 4
```
