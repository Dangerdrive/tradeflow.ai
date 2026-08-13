"""Testes canary da cadeia LLM (Fase U3): chromadb 1.x, langchain_openai, crewai 1.x.

Sem chamadas de rede pagas: instanciação é lazy e o chromadb usa diretório
temporário.
"""


def test_chromadb_create_add_query(tmp_path) -> None:
    import chromadb

    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    collection = client.create_collection("ncm_test")

    collection.add(
        ids=["1", "2"],
        embeddings=[[0.1, 0.2], [0.9, 0.8]],
        metadatas=[{"ncm": "8528.72.00"}, {"ncm": "9405.40.10"}],
        documents=["televisor led 55 polegadas", "lampada led 9w"],
    )

    resultado = collection.query(query_embeddings=[[0.11, 0.19]], n_results=1)
    assert resultado["ids"][0][0] == "1"


def test_langchain_openai_instancia_sem_chamada() -> None:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings

    # Instanciação é lazy — nenhuma chamada de rede é feita aqui.
    chat = ChatOpenAI(model="gpt-4o-mini", api_key="sk-placeholder")
    emb = OpenAIEmbeddings(model="text-embedding-3-small", api_key="sk-placeholder")

    assert chat.model_name == "gpt-4o-mini"
    assert emb.model == "text-embedding-3-small"


def test_crewai_instancia_sem_kickoff() -> None:
    from crewai import Agent, Crew, Task

    agente = Agent(
        role="Especialista em Comércio Exterior",
        goal="Extrair campos de faturas comerciais",
        backstory="Você tem 10 anos de experiência em importação.",
        llm="openai/gpt-4o-mini",
    )
    tarefa = Task(
        description="Extraia os campos da fatura.",
        expected_output="JSON com os campos extraídos.",
        agent=agente,
    )
    crew = Crew(agents=[agente], tasks=[tarefa])

    assert len(crew.agents) == 1
    assert len(crew.tasks) == 1
    assert agente.role == "Especialista em Comércio Exterior"
