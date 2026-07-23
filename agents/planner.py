from typing import List
from graph.state import AgentState
from dotenv import load_dotenv
load_dotenv()
from langchain_mistralai import ChatMistralAI
from pydantic import BaseModel, Field

from graph.state import AgentState

llm = ChatMistralAI(
    model="mistral-small-2506",
    temperature=0
)

class DevelopmentPlan(BaseModel):
    tasks: List[str] = Field(
        description="A list of ordered development tasks."
    )

planner_llm = llm.with_structured_output(
    DevelopmentPlan
)

PLANNER_PROMPT = """
You are the Planner Agent in an Autonomous AI Software engineer.
Your job is to convert a software requirement into a clear,
ordered development plan.

Rules:

1. Do not write code.
2. Break the project into small actionable tasks.
3. Order tasks according to their dependencies.
4. Include development and testing tasks.
5. Do not include unnecessary tasks.

Return only the development plan.
"""

def planner_agent(state: AgentState):
    prompt=f"""
    {PLANNER_PROMPT}

    User Request:
    {state["user_request"]}
    """
    plan = planner_llm.invoke(prompt)
    print("==========Planner===============")
    
    for index, task in enumerate(plan.tasks, start=1):
        print(f"{index}.{task}")
    
    print("===============================")
    print()
    state['next_agent'] = "manager"
    return {
        "plan":plan.tasks,
    }