import sys
import time

sys.stdout.reconfigure(line_buffering=True)

from typing import Literal

from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END

from graph.state import AgentState

from agents.planner import planner_agent
from agents.architect import architect_agent
from agents.coder import coder_node
from agents.tester import tester_agent
from agents.debugger import debugger_agent
from agents.reviewer import reviewer_agent

from prompts.manager_prompt import MANAGER_PROMPT

# =========================================================
# LLM
# =========================================================

llm = ChatMistralAI(
    model="codestral-latest",
    temperature=0,
    max_retries=5,
    timeout=60,
)


# =========================================================
# MANAGER DECISION
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
        "done",
    ] = Field(
        description="The next specialized agent that should execute."
    )

    reason: str = Field(
        description="Why this agent should execute next."
    )

    task: str = Field(
        description="The specific task assigned to the agent."
    )


manager_llm = llm.with_structured_output(
    ManagerDecision
)


# =========================================================
# MANAGER NODE
# =========================================================

def manager_agent(state: AgentState):
    time.sleep(1)
    prompt = f"""
{MANAGER_PROMPT}

==================================================
USER REQUEST
==================================================

{state["user_request"]}

==================================================
CURRENT PLAN
==================================================

{state["plan"]}

==================================================
ARCHITECTURE
==================================================

{state["architecture"]}

==================================================
CURRENT TASK
==================================================

{state["current_task"]}

==================================================
COMPLETED TASKS
==================================================

{state["completed_tasks"]}

==================================================
FAILED TASKS
==================================================

{state["failed_tasks"]}

==================================================
CODER RESULT
==================================================

{state.get("coder_result", {})}

==================================================
TEST RESULT
==================================================

{state.get("test_result", {})}

==================================================
DEBUG RESULT
==================================================

{state.get("debug_result", {})}

==================================================
REVIEW RESULT
==================================================

{state.get("review_result", {})}

==================================================
DECIDE NEXT STEP
==================================================

Select exactly one next agent.

Assign a specific task to that agent.
"""

    decision = manager_llm.invoke(
        prompt
    )

    print(
        "\n================ MANAGER ================"
    )

    print(
        "Next Agent:",
        decision.next_agent
    )

    print(
        "Task:",
        decision.task
    )

    print(
        "Reason:",
        decision.reason
    )

    print(
        "=========================================\n"
    )

    return {
        "next_agent": decision.next_agent,
        "current_task": decision.task,
        "manager_reason": decision.reason,
    }


# =========================================================
# MANAGER ROUTER
# =========================================================

def route_manager(state: AgentState):

    return state["next_agent"]


# =========================================================
# PLACEHOLDER AGENTS
# =========================================================


def documentation_agent(state: AgentState):
    print("Documentation Agent Running...")
    current_task = state.get("current_task", "")
    completed_tasks = list(state.get("completed_tasks", []))
    if current_task and current_task not in completed_tasks:
        completed_tasks.append(current_task)
    return {"completed_tasks": completed_tasks}


#==========================================================
# Coder Processor Logic
# =========================================================
def process_coder_result(state: AgentState):

    coder_result = state.get("coder_result", {})

    completed_tasks = list(
        state.get("completed_tasks", [])
    )

    failed_tasks = list(
        state.get("failed_tasks", [])
    )

    current_task = state.get(
        "current_task",
        ""
    )

    if coder_result.get("completed"):

        if current_task and current_task not in completed_tasks:
            completed_tasks.append(current_task)

        if current_task in failed_tasks:
            failed_tasks.remove(current_task)

        print(
            f" Coder completed task: {current_task}"
        )

    else:

        if current_task and current_task not in failed_tasks:
            failed_tasks.append(current_task)

        print(
            f" Coder failed task: {current_task}"
        )

    return {
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
    }

# =========================================================
# BUILD MAIN GRAPH
# =========================================================

builder = StateGraph(
    AgentState
)


# =========================================================
# MANAGER
# =========================================================

builder.add_node(
    "manager",
    manager_agent
)


# =========================================================
# SPECIALIZED AGENTS
# =========================================================

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
    coder_node
)

builder.add_node(
    "process_coder_result",
    process_coder_result
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
# START
# =========================================================

builder.add_edge(
    START,
    "manager"
)


# =========================================================
# MANAGER ROUTING
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
        "done": END,
    },
)


# =========================================================
# RETURN TO MANAGER
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
    "process_coder_result"
)

builder.add_edge(
    "process_coder_result",
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
# COMPILE
# =========================================================

graph = builder.compile()