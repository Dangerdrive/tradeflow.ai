# Plano de Upgrade Amplo de Dependências — TradeFlow

> Documento de planejamento do upgrade das dependências (opção 2) para eliminar as vulnerabilidades apontadas pelo `pip-audit` e sair das versões de 2024. **Inclui a estratégia de testes para comprovar o sucesso.**

**Data:** 2026-08-13
**Estado:** Planejado (não executado)
**Motivação:** `pip-audit` reportou **104 CVEs em 19 pacotes** (pypdf, pillow, langchain, streamlit, starlette, etc.) devido a pins de 2024.

---

## 1. Objetivo e escopo

Subir todas as dependências para versões estáveis de 2025/2026, removendo as vulnerabilidades conhecidas **sem regressão funcional** e mantendo o projeto rodando em Python 3.12.

**Fora de escopo:** mudanças de arquitetura, novas features das Fases 1+, refatoração de código de domínio (salvo o mínimo necessário para adaptar a APIs quebradas).

---

## 2. Riscos principais do upgrade amplo

| Risco | Impacto | Mitigação |
| :--- | :--- | :--- |
| **LangChain 1.0** quebrou APIs (`langchain_community`, loaders, `ChatOpenAI`) | Alto | Upgrade isolado na fase U3 + testes de importação/canary |
| **CrewAI** mudou a API entre 0.4x e 1.x (e pode ter abandonado `embedchain`) | Alto | Verificar release notes; instanciar Agent/Task/Crew sem executar |
| **ChromaDB 1.x** mudou API de persistência/collection | Médio | Teste canary de create/add/query |
| **OpenAI 2.x** mudou interface do client | Médio | Teste de instanciação mockada (sem custo) |
| **PyPDF2 está deprecado** → substituir por `pypdf` | Baixo | pdfplumber já usa pypdf internamente |
| **pydantic 2.x** mudanças de comportamento | Baixo | Já usamos v2; validar `pydantic-settings` |
| Diamond dependency (duplicação de `langchain-core`/`chromadb`) | Médio | `uv tree` + `uv pip check` |
| Rollback inviável | Alto | Branch dedicada + `uv.lock` versionado |

---

## 3. Estratégia de execução (em fases, com rollback)

Trabalhar em branch `chore/upgrade-deps` e revalidar ao final de **cada fase**. O `uv.lock` é versionado no Git, o que garante **rollback determinístico**.

| Fase | Grupos de pacotes | Risco |
| :--- | :--- | :--- |
| **U0** | Baseline: rodar suite atual + `pip-audit` antes de mexer | — |
| **U1** | Ferramentas dev: `ruff`, `black`, `pytest`, `pip-audit` | Baixo |
| **U2** | Infra segura: `pydantic`, `pydantic-settings`, `sqlalchemy`, `alembic`, `pandas`, `scikit-learn`, `joblib`, `fastapi`/`starlette`/`uvicorn`, `streamlit`, `pillow`, `pypdf` (substitui PyPDF2), `pdfplumber`, `python-multipart`, `python-dotenv`, `psycopg2-binary` | Médio |
| **U3** | Cadeia LLM: `openai`, `langchain`/`langchain-core`/`langchain-openai`/`langchain-community`, `crewai`, `chromadb` (libera a constraint `<0.5.0` se o novo crewai não depender de `embedchain`) | **Alto** |
| **U4** | Revalidação completa + `pip-audit` + **teste de rollback** | — |

---

## 4. Mapa de versões (atual → alvo)

> As versões-alvo exatas são resolvidas pelo `uv` na execução; a tabela indica a linha major e as mudanças esperadas.

| Pacote | Atual | Alvo | Observação de breaking change |
| :--- | :--- | :--- | :--- |
| langchain | 0.2.7 | 1.x | Split em `langchain-classic`/`langchain-community`; loaders mudaram de pacote |
| langchain-core | 0.2.43 (transitivo) | 1.x | Base de tudo; testar imports |
| langchain-openai | 0.1.12 | 1.x | Compatível com openai 2.x |
| langchain-community | 0.2.7 | 0.3+/1.x | Muitos loaders migraram de pacote |
| crewai | 0.41.0 | 1.x | Verificar se ainda traz `embedchain` (a origem da constraint do chromadb) |
| chromadb | 0.4.24 | 1.x | API de collection/persistência |
| openai | 1.35.13 | 2.x | Client síncrono/assíncrono |
| pydantic | 2.7.4 | 2.x (última) | Já em v2; validar settings |
| fastapi | 0.111.0 | 0.11x | starlette/pydantic internos |
| streamlit | 1.36.0 | 1.5x | Alguns componentes mudaram |
| PyPDF2 | 3.0.1 | **removido** | Substituir por `pypdf` 6.x |
| pypdf | 4.3.1 (transitivo) | 6.x | API de leitura |
| pdfplumber | 0.11.2 | última | Usa pypdf internamente |
| pillow | 10.4.0 | 12.x | — |
| pandas | 2.2.2 | 2.3.x | — |
| scikit-learn | 1.5.1 | 1.6/1.7 | — |
| sqlalchemy | 2.0.31 | 2.0.x (última) | — |
| black | 24.4.2 | 26.x | Calendário de versão |
| ruff | 0.5.1 | 0.x/1.x | Novas regras podem aparecer |
| pytest | 8.2.2 | 8.x/9.x | — |
| pip-audit | 2.7.3 | última | — |

---

## 5. Passos de migração (por fase)

1. `git checkout -b chore/upgrade-deps` + commit do estado atual (ponto de restauração).
2. Editar `pyproject.toml` (fase U1 → U2 → U3, separadamente).
3. `uv lock` — resolver conflitos; usar `uv add <pkg>` quando precisar de resolução assistida.
4. `uv sync` — instalar.
5. Rodar a suite de testes (seção 6) e o `pip-audit`.
6. Commit por fase; ao final, merge na `main`.

---

## 6. Plano de testes — "como saber se o upgrade foi um sucesso"

### 6.1 Testes de resolução (comandos, não pytest)

| Checagem | Comando | Critério de sucesso |
| :--- | :--- | :--- |
| Lock sem conflitos | `uv lock` | Resolve sem erros de conflito de dependência |
| Árvore sem duplicatas | `uv tree` | Sem duas versões simultâneas de `langchain-core`, `chromadb`, `pydantic` |
| Dependências íntegras | `uv pip check` | "No broken requirements found" |
| Lock versionado | `git status` | `uv.lock` e `pyproject.toml` alterados e commitáveis |

### 6.2 Testes de importação (smoke por dependência)

Criar `tests/test_imports.py` que importa cada biblioteca e **afirma a versão major** esperada — detecta breaking changes de caminho de importação na hora.

```python
import importlib

EXPECTED = [
    ("pydantic", "2"),
    ("sqlalchemy", "2"),
    ("fastapi", "0"),
    ("streamlit", "1"),
    ("pandas", "2"),
    ("sklearn", "1"),
    ("chromadb", "1"),
    ("openai", "2"),
    ("langchain_core", "1"),
    ("pypdf", "6"),
    ("crewai", "1"),
]

def test_importa_e_versao():
    for mod, major in EXPECTED:
        m = importlib.import_module(mod)
        assert getattr(m, "__version__", "0").split(".")[0] == major
```

**Sucesso:** todos os imports resolvem e as majors são as esperadas.

### 6.3 Testes de regressão da Fase 0 (já existem)

- `tests/test_smoke.py` (config via `pydantic-settings`, logging JSON) **deve continuar verde**.
- **Sucesso:** `uv run pytest` → 3 passed sem alterar os arquivos de domínio.

### 6.4 Testes de contrato (schemas inalterados)

- `config/settings.py` continua expondo exatamente os mesmos campos (`openai_api_key`, `database_url`, `chroma_persist_dir`, `app_name`, `log_level`, ...).
- `utils/logging.py` continua produzindo JSON com `ts`, `level`, `logger`, `message`, `correlation_id`.
- **Sucesso:** nenhum teste de contrato quebra; se quebrar, é breaking change a tratar.

### 6.5 Testes canary por dependência (integração mínima, sem custo de LLM)

Criar `tests/test_canary_deps.py` com cenários mínimos que exercitam a **API real** de cada lib sem chamadas externas pagas:

| Dependência | Teste canary |
| :--- | :--- |
| `chromadb` | Criar `PersistentClient` em dir temporário, criar collection, `add` + `query` |
| `sqlalchemy` | Engine SQLite em memória, criar tabela, inserir e consultar (CRUD) |
| `langchain_openai` | Instanciar `ChatOpenAI` e `OpenAIEmbeddings` **mockando o client** (sem chamada real) |
| `crewai` | Instanciar `Agent`, `Task` e `Crew` **sem `kickoff()`** (valida a API) |
| `pdfplumber`/`pypdf` | Abrir um PDF de amostra e extrair texto |
| `sklearn`/`pandas` | Treinar um `LinearRegression` em dados sintéticos |
| `fastapi` | Criar `FastAPI()` + `TestClient` com um endpoint trivial |
| `streamlit` | `import streamlit` + smoke de criação de app (sem servidor) |

**Sucesso:** todos os canaries passam, provando que as APIs novas funcionam no nosso código.

### 6.6 Testes E2E do pipeline (quando Fases 1+ existirem)

- Mockar o LLM (determinístico) e executar o fluxo completo: PDF → extração → NCM → predição → persistência.
- **Sucesso:** saída idêntica (ou superior) à do baseline, com o pipeline verde.

> Para o upgrade atual, como as Fases 1+ ainda não foram implementadas, os canaries (6.5) cobrem os pontos de integração críticos.

### 6.7 Segurança

- `uv run pip-audit` → **0 vulnerabilidades críticas/altas** (meta); médias/baixas devem ser documentadas e aceitas.
- **Sucesso:** eliminação das 104 CVEs ou redução a uma lista aprovada.

### 6.8 Performance (regressão de latência)

- Medir `time uv run pytest` antes e depois do upgrade.
- Medir tempo de import dos módulos pesados (`chromadb`, `streamlit`, `langchain`).
- **Sucesso:** sem regressão significativa (> 20% de aumento é alarme).

### 6.9 Qualidade de código

- `uv run ruff check .` e `uv run black --check .` verdes.
- **Sucesso:** se novas regras do ruff aparecerem, corrigir ou justificar no `pyproject.toml`.

---

## 7. Critérios de aceitação (definição de sucesso)

O upgrade é considerado **sucesso** quando, **no Python 3.12**:

1. ✅ `uv lock` resolve sem conflitos e `uv pip check` está limpo.
2. ✅ `uv tree` não mostra duplicidade de majors críticos.
3. ✅ `uv run pytest` verde (smoke + imports + canary + contrato).
4. ✅ `uv run pip-audit` sem vulnerabilidades críticas/altas (ou lista aprovada).
5. ✅ `uv run ruff check .` e `uv run black --check .` verdes.
6. ✅ Teste de rollback executado com sucesso (seção 8).
7. ✅ Fase 0 funcionalmente idêntica (schemas/config inalterados).

---

## 8. Plano de rollback

1. O `uv.lock` é versionado no Git — **reverter é determinístico**.
2. Comando de rollback:

```bash
git checkout main -- pyproject.toml uv.lock
uv sync
uv run pytest
```

3. **Teste de rollback obrigatório** (fase U4): simular a reversão e confirmar que a suite volta a ficar verde.
4. Manter o commit de baseline tagueado (`git tag pre-upgrade`).

---

## 9. Checklist de execução

- [x] U0: baseline (pytest + pip-audit) registrado
- [x] Branch `chore/upgrade-deps` + tag `pre-upgrade`
- [x] U1: dev tools atualizadas e verdes
- [x] U2: infra segura atualizada e verdes (canary + contrato)
- [x] U3: cadeia LLM atualizada (chromadb liberado da constraint do embedchain)
- [x] U4: `pip-audit` com exceção documentada + revalidação
- [ ] Merge na `main` + CI verde
- [x] Memória do repositório atualizada com as novas versões e constraints

---

## 10. Resultados da execução (2026-08-13)

**Evolução do `pip-audit`:**

| Fase | Vulnerabilidades | Pacotes |
| :--- | :---: | :---: |
| Baseline (U0) | 104 | 19 |
| U1 (dev tools) | 112* | 17 |
| U2 (infra) | 65 | 10 |
| U3 (LLM chain) | **1** | **1** |

> *O número subiu entre U0 e U1 porque o `pip-audit` re-baixou um banco de
> advisories mais atualizado; o importante é a redução a partir daí.

**Estado final:**
- `crewai` 1.15.15, `langchain` 1.3.15, `openai` 2.54.0, `chromadb` 1.1.1,
  `pypdf` 6.16.0, `fastapi` 0.141.1, `streamlit` 1.61.1, `pydantic` 2.12.5.
- Vuln restante: **chromadb 1.1.1 (PYSEC-2026-311)** — sem versão fix publicada;
  aceita e documentada; CI usa `pip-audit --ignore-vuln PYSEC-2026-311`.
- `requires-python` restrito a `>=3.11,<3.13` (3.13/3.14 quebram a resolução
  universal do lock).
- **15 testes verdes** (smoke + imports + canary U2/U3), `ruff` e `black` OK.

## 11. Próximo passo

- Revisar/mergear a branch `chore/upgrade-deps` na `main` (PR para
  `Dangerdrive/tradeflow.ai`) e validar o CI no GitHub.
- Reavaliar a vuln do chromadb a cada upgrade do crewai.

