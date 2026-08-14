"""Definição dos agentes CrewAI do TradeFlow (Fase 5).

Estes agentes ilustram a orquestração com CrewAI (roles/goals/tasks). O
pipeline padrão (``agents/pipeline.py``) executa os módulos de domínio
diretamente — determinístico e testável sem custo de LLM — mas esta
definição mostra o mapeamento equivalente em CrewAI para a demo/vídeo.

Não é chamado pelo pipeline principal; use ``build_crew`` para a demo.
"""

from __future__ import annotations

from typing import Any

from crewai import Agent, Crew, Task

# --- Agentes ---------------------------------------------------------------

AGENTE_EXTRATOR = dict(
    role="Especialista em Comércio Exterior",
    goal="Extrair campos estruturados de Commercial Invoice com precisão",
    backstory=(
        "Você tem 10 anos de experiência em importação e leitura de faturas "
        "comerciais. Conhece incoterms, NCM e documentação aduaneira."
    ),
    llm="openai/gpt-4o-mini",
)

AGENTE_CLASSIFICADOR = dict(
    role="Classificador Fiscal",
    goal="Sugerir os códigos NCM mais prováveis para cada produto",
    backstory=(
        "Você é um analista fiscal especializado na Tabela TIPI e classificação "
        "fiscal de mercadorias importadas."
    ),
    llm="openai/gpt-4o-mini",
)

AGENTE_PREDITOR = dict(
    role="Analista Preditivo",
    goal="Estimar o prazo de desembaraço aduaneiro a partir de dados históricos",
    backstory=(
        "Você analisa dados de importações para prever prazos e identificar " "gargalos logísticos."
    ),
    llm="openai/gpt-4o-mini",
)


def build_agents() -> list[Agent]:
    """Instancia os três agentes (lazy — nenhuma chamada de LLM aqui)."""
    return [
        Agent(role=a["role"], goal=a["goal"], backstory=a["backstory"], llm=a["llm"])
        for a in (AGENTE_EXTRATOR, AGENTE_CLASSIFICADOR, AGENTE_PREDITOR)
    ]


def build_tasks(agentes: list[Agent]) -> list[Task]:
    """Cria as tasks encadeadas (extração -> classificação -> predição)."""
    extrator, classificador, preditor = agentes

    tarefa_extracao = Task(
        description=(
            "Extraia do PDF de fatura comercial os campos: numero_fatura, "
            "fornecedor, valor_total_usd, peso_bruto_kg, incoterm, volumes e itens."
        ),
        expected_output="JSON com os campos extraídos da fatura.",
        agent=extrator,
    )
    tarefa_classificacao = Task(
        description=(
            "Com base na descrição dos itens extraídos, sugira os 3 códigos NCM "
            "mais prováveis usando a Tabela TIPI."
        ),
        expected_output="Lista de códigos NCM sugeridos com descrição e alíquota.",
        agent=classificador,
    )
    tarefa_predicao = Task(
        description=(
            "Com base em peso, valor, volumes, incoterm e tipo de produto, estime "
            "o prazo de desembaraço em dias."
        ),
        expected_output="Prazo estimado em dias inteiros.",
        agent=preditor,
    )
    return [tarefa_extracao, tarefa_classificacao, tarefa_predicao]


def build_crew() -> Crew:
    """Monta o Crew completo (para a demo CrewAI)."""
    agentes = build_agents()
    tarefas = build_tasks(agentes)
    return Crew(agents=agentes, tasks=tarefas)


def run_crew_kickoff(**kwargs: Any) -> Any:
    """Executa o crew (requer LLM; usado apenas na demo com chave)."""
    return build_crew().kickoff(**kwargs)
