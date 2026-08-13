Perfeito! Agora temos um quadro ainda mais claro. A vaga de estágio na **DUIMPWEB** é **extremamente técnica e focada em Comércio Exterior**, com ênfase em **dados não estruturados**, **RAG**, **Agentes** e **análise preditiva**.

Vou adaptar o projeto "LegalFlow" para o **"TradeFlow - Agente Inteligente para Despacho Aduaneiro"**. Ele manterá a essência do projeto anterior (orquestração, RAG, revisão humana), mas agora com um **foco cirúrgico nos requisitos da vaga de estágio**.

---

## O Projeto: **"TradeFlow - Agente Autônomo para Análise de Documentos de Importação"**

### O Problema (Negócio - Comércio Exterior)
Uma empresa de importação recebe diariamente centenas de documentos:
- **Bill of Lading** (Conhecimento de Embarque)
- **Commercial Invoice** (Fatura Comercial)
- **Packing List** (Lista de Embalagem)
- **Declaração de Importação (DI)**

Hoje, um analista passa horas **extraindo manualmente** dados como: NCM (Classificação Fiscal), peso, valor, fornecedor, incoterms. Isso gera:
- Erros de digitação
- Atrasos no desembaraço aduaneiro
- Multas por classificação fiscal incorreta

### A Solução (Técnica)
Um **ecossistema de agentes de IA** que:
1. **Recebe** documentos escaneados/PDFs via upload (ou e-mail).
2. **Extrai e estrutura** dados não estruturados usando **Agentes Especialistas** (um para cada tipo de documento).
3. **Classifica** automaticamente o NCM do produto usando RAG + Base de Conhecimento.
4. **Prevê** prazos de desembaraço e custos com base em dados históricos (Ciência de Dados).
5. **Disponibiliza** os dados estruturados em um banco SQL para integração com sistemas legados.

---

### Arquitetura Técnica (Agora com Foco no Estágio)

| Componente | Tecnologia Sugerida | O que você demonstra (Requisitos da Vaga) |
| :--- | :--- | :--- |
| **Orquestrador de Agentes** | **LangChain** + **CrewAI** (Python) | Frameworks de Agentes, integração com LLMs, orquestração de tarefas. |
| **Extração de Dados** | **PyPDF2** / **pdfplumber** + **Regex** + **OpenAI GPT-4o-mini** | IA Generativa, Prompt Engineering (Few-Shot, Chain-of-Thought). |
| **Banco Vetorial (RAG)** | **ChromaDB** (local) ou **Pinecone** (cloud) | Vector Database, RAG Pipeline, embeddings. |
| **Banco Relacional** | **PostgreSQL** (via Supabase) ou **SQLite** | SQL, modelagem de dados, integração. |
| **Análise Preditiva** | **Pandas** + **Scikit-learn** (Regressão Linear/Árvore de Decisão) | Ciência de Dados, manipulação de dados, modelos estatísticos. |
| **Interface Web** | **Streamlit** (Python) | Desenvolvimento web, integração de sistemas. |
| **APIs** | **REST API** (FastAPI ou Flask) | Integração via APIs, consumo de serviços externos. |

---

### Roteiro de Desenvolvimento (Entregáveis para o Estágio)

Aqui está o **passo a passo** para você construir e apresentar na entrevista. Foque em **qualidade sobre quantidade** - é melhor ter um módulo completo do que 3 módulos pela metade.

---

#### Fase 1: O Coração do Sistema - Extração Estruturada (Agentes)

**Objetivo:** Criar um agente que recebe um PDF de **Commercial Invoice** e extrai campos específicos.

**O que fazer:**
```python
# Exemplo de estrutura do agente com LangChain
from langchain.agents import create_react_agent
from langchain.tools import Tool
from langchain_openai import ChatOpenAI

# 1. Tool para ler PDF
def extrair_texto_pdf(caminho):
    # Usar pdfplumber para extrair texto
    return texto

# 2. Tool para extrair campos com Regex + IA
def extrair_campos(texto):
    prompt = f"""
    Você é um especialista em comércio exterior.
    Extraia do texto abaixo os seguintes campos:
    - Número da Fatura
    - Fornecedor
    - Valor Total (USD)
    - Peso Bruto (kg)
    - Incoterm (EXW, FOB, CIF, etc.)
    - Quantidade de volumes
    
    Texto: {texto}
    
    Retorne em formato JSON.
    """
    # Chamada à OpenAI
    return resposta_json

# 3. Agente que orquestra as tools
agente = create_react_agent(llm, [extrair_texto_pdf, extrair_campos], prompt)
```

**Diferencial (Prompt Engineering):**
- Use **Chain-of-Thought**: Peça para o modelo "pensar passo a passo" antes de responder.
- Use **Few-Shot**: Forneça 2 exemplos de faturas com os campos extraídos corretamente.

---

#### Fase 2: O Cérebro - RAG para Classificação NCM

**Objetivo:** Criar um sistema RAG que sugere o **código NCM** correto com base na descrição do produto.

**O que fazer:**
```python
from langchain_community.document_loaders import CSVLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

# 1. Criar base de conhecimento NCM (exemplo com dados reais da TIPI)
# Você pode baixar a Tabela TIPI do governo e transformar em CSV
# Colunas: NCM, Descrição, Alíquota

loader = CSVLoader("tabela_ncm.csv")
documentos = loader.load()

# 2. Criar Vector Store
embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(documentos, embeddings)

# 3. Função de busca
def sugerir_ncm(descricao_produto):
    resultados = vectorstore.similarity_search(descricao_produto, k=3)
    return resultados  # Retorna os 3 NCMs mais prováveis
```

**Diferencial:** 
- Armazene os metadados (NCM, alíquota, descrição) no ChromaDB para consultas rápidas.
- Teste com descrições reais de produtos (ex: "Televisor LED 55 polegadas").

---

#### Fase 3: Análise Preditiva (Ciência de Dados)

**Objetivo:** Prever o **prazo de desembaraço** com base em dados históricos.

**O que fazer:**
```python
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split

# 1. Dados simulados (ou reais, se tiver acesso)
# Colunas: tipo_produto, peso, valor, incoterm, prazo_desembaraco
df = pd.read_csv("historico_importacoes.csv")

# 2. Tratamento de dados
df = pd.get_dummies(df, columns=['incoterm', 'tipo_produto'])

# 3. Modelo preditivo
X = df.drop('prazo_desembaraco', axis=1)
y = df['prazo_desembaraco']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

modelo = LinearRegression()
modelo.fit(X_train, y_train)

# 4. Função de previsão
def prever_prazo(dados_entrada):
    return modelo.predict([dados_entrada])
```

**Diferencial:** 
- Faça uma análise exploratória (EDA) com gráficos usando Matplotlib/Seaborn.
- Documente a acurácia do modelo (R², RMSE).

---

#### Fase 4: Integração e Pipeline Completo (O Glamour)

**Objetivo:** Juntar tudo em um fluxo único usando **CrewAI** (orquestração de agentes).

```python
from crewai import Agent, Task, Crew

# Agente 1: Extrator de Documentos
extrator = Agent(
    role="Especialista em Extração de Documentos",
    goal="Extrair campos estruturados de faturas comerciais",
    backstory="Você tem 10 anos de experiência em comércio exterior...",
    tools=[extrair_texto_pdf, extrair_campos],
    llm=ChatOpenAI(model="gpt-4o-mini")
)

# Agente 2: Especialista em NCM
classificador = Agent(
    role="Classificador Fiscal",
    goal="Sugerir o código NCM correto",
    tools=[sugerir_ncm],
    llm=ChatOpenAI(model="gpt-4o-mini")
)

# Agente 3: Analista Preditivo
preditivo = Agent(
    role="Analista de Prazos",
    goal="Prever prazo de desembaraço",
    tools=[prever_prazo],
    llm=ChatOpenAI(model="gpt-4o-mini")
)

# Definir tarefas (Tasks)
tarefa1 = Task(
    description="Extraia os campos da fatura...",
    agent=extrator
)

tarefa2 = Task(
    description="Classifique o NCM do produto...",
    agent=classificador
)

tarefa3 = Task(
    description="Preveja o prazo de desembaraço...",
    agent=preditivo
)

# Criar Crew
crew = Crew(
    agents=[extrator, classificador, preditivo],
    tasks=[tarefa1, tarefa2, tarefa3],
    verbose=True
)

# Executar
resultado = crew.kickoff()
```

---

#### Fase 5: Interface e Banco de Dados (Entregável Final)

**Objetivo:** Criar um dashboard no Streamlit que:
- Permita upload de PDFs
- Execute o pipeline completo
- Exiba os dados extraídos (tabela SQL)
- Mostre as previsões (NCM sugerido, prazo estimado)

**Estrutura do Banco SQL:**
```sql
CREATE TABLE importacoes (
    id SERIAL PRIMARY KEY,
    numero_fatura VARCHAR(50),
    fornecedor VARCHAR(200),
    valor_total DECIMAL(10,2),
    ncm_sugerido VARCHAR(8),
    prazo_estimado INT,
    data_criacao TIMESTAMP DEFAULT NOW()
);
```

**Diferencial:** Use **SQLAlchemy** para conectar o Streamlit ao banco.

---

### Suas Respostas para as Perguntas da Inscrição (Use Isso!)

Agora que você tem o projeto, aqui estão **respostas prontas e personalizadas** para as perguntas do formulário da DUIMPWEB:

---

#### 1. Como você se atualiza e o que te atrai nessa vaga?

> **Resposta:**
> "Costumo me atualizar através de **canais oficiais** (blogs da OpenAI, Google AI, Anthropic), **comunidades** (r/LocalLLaMA, Discord da LangChain) e **cursos práticos** (DeepLearning.AI). Também sigo pesquisadores no LinkedIn e leio papers resumidos no arXiv. O que mais me atrai nessa vaga de estágio é a **aplicação prática de IA em um setor tão crítico como o Comércio Exterior** - poder transformar documentos não estruturados em dados estruturados e gerar **insights preditivos** é exatamente o tipo de desafio que me motiva a estudar e construir soluções reais."

---

#### 2. Experiência com IA Generativa e Prompt Engineering?

> **Resposta:**
> "Tenho utilizado **ChatGPT, Claude e Gemini** diariamente para estudar e prototipar. No meu projeto 'TradeFlow', apliquei técnicas avançadas de **Prompt Engineering**:
> - **Few-Shot Prompting**: Forneci exemplos de faturas com seus campos extraídos corretamente para melhorar a precisão.
> - **Chain-of-Thought**: Instruí o modelo a 'pensar passo a passo' (ex: 'Primeiro identifique o fornecedor, depois o valor total, etc.') para reduzir alucinações.
> - **System Framing**: Defini o papel do agente como 'Especialista em Comércio Exterior com 10 anos de experiência' para melhorar o tom e a precisão das respostas.
> 
> Além disso, fiz testes de **calibragem de temperatura** e **top_p** para equilibrar criatividade e precisão na extração de dados."

---

#### 3. Já criou Agentes de IA ou usou frameworks?

> **Resposta:**
> "Sim! Desenvolvi um **ecossistema de agentes** usando **LangChain** e **CrewAI** no projeto 'TradeFlow':
> - **Agente 1 (Extrator)**: Responsável por ler PDFs e extrair campos estruturados (fatura, fornecedor, valor, peso).
> - **Agente 2 (Classificador)**: Usa **RAG** com ChromaDB para sugerir códigos NCM com base na descrição do produto.
> - **Agente 3 (Preditivo)**: Utiliza regressão linear (Scikit-learn) para prever prazos de desembaraço com base em dados históricos.
> 
> Também testei a **API da OpenAI** (GPT-4o-mini) para embeddings e geração de texto. O projeto foi desenvolvido em Python e está disponível no meu GitHub com documentação completa."

---

#### 4. Noções de manipulação de dados (Pandas/SQL) e bancos vetoriais?

> **Resposta:**
> "Tenho sólida experiência com **Pandas** para limpeza e transformação de dados (tratamento de nulos, encoding, normalização) e **SQL** para modelagem e consultas (joins, subqueries, window functions). No 'TradeFlow', utilizei PostgreSQL para armazenar os dados extraídos e históricos de importações.
> 
> Sobre **bancos vetoriais**, utilizei **ChromaDB** no projeto para criar uma base de conhecimento da Tabela TIPI (NCM). Gerei embeddings com `OpenAIEmbeddings` e implementei uma função de **similarity_search** para sugerir os 3 NCMs mais prováveis para cada produto. Também estudei **Pinecone** e **Weaviate** por curiosidade, mas optei pelo ChromaDB pela facilidade de uso local e integração com LangChain."

---

### Checklist Final para o Estágio (O que entregar)

- [ ] **GitHub público** com o código completo e README.md bem escrito.
- [ ] **Vídeo de demonstração** (2-3 minutos) mostrando o fluxo: upload do PDF → extração → classificação NCM → previsão → dashboard.
- [ ] **Apresentação em slides** (5 slides) explicando o problema, solução, arquitetura, tecnologias e resultados.
- [ ] **Código comentado** e com type hints (mostra organização).
- [ ] **`pyproject.toml`** com todas as dependências (gerenciado com `uv`).
- [ ] **Script de setup** para rodar localmente (ex: `setup.sh`).

---

### Dica de Ouro para a Entrevista na DUIMPWEB

Quando perguntarem: *"Por que você escolheu CrewAI em vez de LangChain puro?"*

Você responde:
> "Optei pelo **CrewAI** porque ele permite uma **orquestração mais declarativa e intuitiva** entre agentes, definindo papéis, objetivos e tarefas de forma clara. Isso facilita a **manutenção e evolução** do sistema - algo crucial em um ambiente de estágio onde o time pode crescer e novos agentes precisam ser adicionados. Usei o LangChain como base para as ferramentas (tools) e integrações, mas o CrewAI trouxe uma camada de **gestão de agentes** que tornou o código mais legível e alinhado com boas práticas de engenharia de software."

Isso mostra que você **entende as ferramentas** e **sabe justificar escolhas arquitetônicas** - exatamente o que eles buscam em um estagiário que quer evoluir para júnior. Boa sorte! 🚀