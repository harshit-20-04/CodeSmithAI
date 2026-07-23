from typing import TypedDict, List, Literal
from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from graph.state import AgentState
from agents.planner import planner_agent
from agents.architect import architect_agent
load_dotenv()
# =========================================================
# 2. LLM
# =========================================================

llm = ChatMistralAI(
    model="mistral-small-2506",
    temperature=0
)


# =========================================================
# 3. MANAGER PROMPT
# =========================================================


MANAGER_PROMPT = """

You are the Manager Agent of an autonomous AI software engineer.

Your job is to coordinate specialized software engineering agents.

Available agents:

- planner:
  Creates a development plan.

- architect:
  Designs the software architecture and project structure.

- coder:
  Writes or modifies source code.

- tester:
  Creates and runs tests.

- debugger:
  Investigates and fixes errors.

- reviewer:
  Reviews code quality, correctness and security.

- documentation:
  Creates project documentation.

- done:
  Finishes the workflow.

Follow these rules carefully:

1. If the plan is empty:
   Select "planner".

2. If the plan exists but architecture has not been created:
   Select "architect".

3. If architecture exists and there are incomplete development tasks:
   Select "coder".

4. If code has been implemented but has not been tested:
   Select "tester".

5. If tests fail:
   Select "debugger".

6. After debugging:
   Select "tester".

7. If all tests pass:
   Select "reviewer".

8. If the reviewer approves the project:
   Select "documentation".

9. If documentation is complete:
   Select "done".

10. Never select "planner" if a development plan already exists.

11. Never select "architect" if architecture is already complete.

12. Never select "coder" if there are no implementation tasks remaining.

13. Do not write code yourself.

14. Always consider the current project state before making a decision.

"""


# =========================================================
# 4. MANAGER DECISION
# =========================================================

class ManagerDecision(BaseModel):
    next_agent: Literal[
        "planner",
        "architect",
        "coder",
        "tester",
        "debugger",
        "reviewer",
        "documentation",
        "done"
    ] = Field(
        description="The next specialized agent that should execute."
    )
    reason: str = Field(
        description="Explain why this agent should execute next."
    )
    task: str = Field(
        description="The specific task assigned to the agent."
    )


# =========================================================
# 5. STRUCTURED LLM
# =========================================================

manager_llm = llm.with_structured_output(
    ManagerDecision
)


# =========================================================
# 6. MANAGER NODE
# =========================================================

def manager_agent(state: AgentState):
    prompt = f"""
    {MANAGER_PROMPT}

    USER REQUEST:
    {state["user_request"]}
    
    CURRENT PLAN:
    {state["plan"]}
    
    CURRENT TASK:
    {state["current_task"]}
    
    COMPLETED TASKS:
    {state["completed_tasks"]}
    
    FAILED TASKS:
    {state["failed_tasks"]}

    Decide the next step.
    """

    decision = manager_llm.invoke(prompt)
    print("\n================ MANAGER ================")
    print("Next Agent:", decision.next_agent)
    print("Task:", decision.task)
    print("Reason:", decision.reason)
    print("=========================================\n")

    return {
        "next_agent": decision.next_agent,
        "current_task": decision.task,
        "manager_reason": decision.reason
    }


# =========================================================
# 7. ROUTER
# =========================================================

def route_manager(state: AgentState):
    return state["next_agent"]


# =========================================================
# 8. PLACEHOLDER AGENTS
# =========================================================



def coder_agent(state: AgentState):
    print("Coder Agent Running...")
    return {}


def tester_agent(state: AgentState):
    print("Tester Agent Running...")
    return {}


def debugger_agent(state: AgentState):
    print("Debugger Agent Running...")
    return {}


def reviewer_agent(state: AgentState):
    print("Reviewer Agent Running...")
    return {}


def documentation_agent(state: AgentState):
    print("Documentation Agent Running...")
    return {}


# =========================================================
# 9. BUILD GRAPH
# =========================================================

builder = StateGraph(AgentState)


# Manager
builder.add_node(
    "manager",
    manager_agent
)


# Specialized agents
builder.add_node(
    "planner",
    planner_agent
)

builder.add_node(
    "architect",
    architect_agent
)

builder.add_node(
    "coder",
    coder_agent
)

builder.add_node(
    "tester",
    tester_agent
)

builder.add_node(
    "debugger",
    debugger_agent
)

builder.add_node(
    "reviewer",
    reviewer_agent
)

builder.add_node(
    "documentation",
    documentation_agent
)


# =========================================================
# 10. START
# =========================================================

builder.add_edge(
    START,
    "manager"
)


# =========================================================
# 11. MANAGER ROUTING
# =========================================================

builder.add_conditional_edges(
    "manager",
    route_manager,
    {
        "planner": "planner",
        "architect": "architect",
        "coder": "coder",
        "tester": "tester",
        "debugger": "debugger",
        "reviewer": "reviewer",
        "documentation": "documentation",
        "done": END
    }
)


# =========================================================
# 12. RETURN TO MANAGER
# =========================================================

builder.add_edge(
    "planner",
    "manager"
)

builder.add_edge(
    "architect",
    "manager"
)

builder.add_edge(
    "coder",
    "manager"
)

builder.add_edge(
    "tester",
    "manager"
)

builder.add_edge(
    "debugger",
    "manager"
)

builder.add_edge(
    "reviewer",
    "manager"
)

builder.add_edge(
    "documentation",
    "manager"
)


# =========================================================
# 13. COMPILE
# =========================================================

graph = builder.compile()

