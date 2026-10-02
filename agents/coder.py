
from typing import List

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, SystemMessage, trim_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from graph.state import AgentState
from graph.coder_state import CoderState

from prompts.coder_prompt import CODER_PROMPT

from tools.filesystem import (
    list_files,
    read_file,
    write_file,
    edit_file,
)
from tools.terminal import run_command


load_dotenv()


# =========================================================
# LLM
# =========================================================

llm = ChatMistralAI(
    model="codestral-latest",
    temperature=0,
)

# =========================================================
# CODER RESULT
# =========================================================

class CoderResult(BaseModel):
    summary: str = Field(
        description="A concise summary of the implementation."
    )

    completed: bool = Field(
        description="Whether the current task was successfully completed."
    )

    created_files: List[str] = Field(
        description="Files created by the coder."
    )

    modified_files: List[str] = Field(
        description="Files modified by the coder."
    )

    errors: List[str] = Field(
        description="Errors encountered during implementation."
    )


coder_result_llm = ChatMistralAI(
    model="codestral-latest",
    temperature=0,
).with_structured_output(CoderResult)


# =========================================================
# TOOLS
# =========================================================

coder_tools = [
    list_files,
    read_file,
    write_file,
    edit_file,
    run_command,
]

coder_llm = llm.bind_tools(coder_tools)

coder_tool_node = ToolNode(coder_tools)


# =========================================================
# CODER NODE
# =========================================================

def coder_agent(state: CoderState):

    system_prompt = f"""
{CODER_PROMPT}

==================================================
CURRENT PROJECT CONTEXT
==================================================

USER REQUEST:
{state.get("user_request", "")}

DEVELOPMENT PLAN:
{state.get("plan", "")}

SOFTWARE ARCHITECTURE:
{state.get("architecture", "")}

CURRENT TASK:
{state.get("current_task", "")}

COMPLETED TASKS:
{state.get("completed_tasks", [])}

FAILED TASKS:
{state.get("failed_tasks", [])}

==================================================
OBJECTIVE
==================================================

Implement the CURRENT TASK inside the project workspace.

Start by inspecting the project.

Use the available tools to perform the actual implementation.

Do not simply describe code.

Actually create or modify files using the tools.

After implementation, verify your changes.

When the task is complete, stop using tools and return a concise summary.
"""

    raw_history = state.get("messages", [])
    
    # Filter out system messages from raw history
    history_messages = [
        msg for msg in raw_history 
        if (getattr(msg, "type", None) or dict(msg).get("role")) != "system"
    ]

    if not any(getattr(m, "type", "") == "human" or getattr(m, "role", "") == "user" for m in history_messages):
        history_messages.insert(
            0,
            HumanMessage(
                content=f"Begin implementing the current task: {state.get('current_task', 'Start initialization.')}"
            )
        )

    # Safely trim history while preserving tool call pairs
    trimmed_history = trim_messages(
        history_messages,
        max_tokens=4000,
        strategy="last",
        token_counter=len,
        allow_partial=False,
        start_on="human",
    )
    if not trimmed_history:
        trimmed_history = history_messages

    messages = [
        SystemMessage(content=system_prompt),
        *trimmed_history,
    ]

    response = coder_llm.invoke(messages)

    tool_names = [tc.get("name") for tc in getattr(response, "tool_calls", [])]
    print(f"\n[Coder] Task: {state.get('current_task')}")
    if tool_names:
        print(f"[Coder] Invoking tool(s): {tool_names}")
    else:
        print(f"[Coder] Implementation step finished.")

    return {
        "messages": [response]
    }


# =========================================================
# TOOL ROUTER
# =========================================================

def route_code(state: CoderState):
    messages = state.get("messages", [])
    if not messages:
        return "finalize"
    last_message = messages[-1]
    if getattr(last_message, "tool_calls", None):
        # Prevent infinite loops where the EXACT same tool call (name and arguments) is repeated consecutively
        recent_calls = []
        for msg in messages:
            if getattr(msg, "tool_calls", None):
                for tc in msg.tool_calls:
                    recent_calls.append((tc.get("name"), str(tc.get("args"))))
        if len(recent_calls) >= 3 and len(set(recent_calls[-3:])) == 1:
            print(f"\n[Coder] Detected identical repeated tool call for '{recent_calls[-1][0]}'. Transitioning to finalize.")
            return "finalize"
        return "tools"
    return "finalize"


# =========================================================
# FINALIZE CODER
# =========================================================

def coder_finalize(state: CoderState):
    
    # 4. 📉 TOKEN SAVER: Compress Message History Objects into Tight Strings
    # Instead of stringifying raw Message objects (which leak massive token metadata arrays),
    # construct a compact historical summary for the structured validator model.
    history_summary = ""
    for idx, msg in enumerate(state.get("messages", [])):
        role = getattr(msg, "type", "message")
        content = getattr(msg, "content", "")
        
        # Truncate content text clips over 300 characters (e.g., massive file dumps)
        if len(content) > 300:
            content = f"{content[:200]}\n... [Truncated to save tokens] ...\n{content[-100:]}"
            
        history_summary += f"\nTurn {idx + 1} ({role}): {content}"

    result_prompt = f"""
You are finalizing the work performed by a Coder Agent.

CURRENT TASK:
{state.get("current_task", "")}

CODER EXECUTION HISTORY SUMMARY:
{history_summary}

Based ONLY on the actual execution history, determine:

1. A concise implementation summary.
2. Whether the task was actually completed.
3. Files created.
4. Files modified.
5. Errors encountered.

Do not claim completion unless the execution history
shows that the implementation was actually performed.

Return the result using the required structured output schema.
"""

    result = coder_result_llm.invoke(result_prompt)

    return {
        "coder_result": result.model_dump()
    }


# =========================================================
# CODER SUBGRAPH INITIALIZATION
# =========================================================

coder_builder = StateGraph(CoderState)
coder_builder.add_node("coder", coder_agent)
coder_builder.add_node("tools", coder_tool_node)
coder_builder.add_node("finalize", coder_finalize)

coder_builder.add_edge(START, "coder")
coder_builder.add_conditional_edges(
    "coder",
    route_code,
    {
        "tools": "tools",
        "finalize": "finalize",
    },
)
coder_builder.add_edge("tools", "coder")
coder_builder.add_edge("finalize", END)

coder_graph = coder_builder.compile()


# =========================================================
# MAIN GRAPH ADAPTER
# =========================================================

def coder_node(state: AgentState):

    current_task = state.get("current_task", "Start initialization.")
    coder_input: CoderState = {
        "user_request": state["user_request"],
        "plan": state["plan"],
        "architecture": state["architecture"],
        "current_task": current_task,
        "completed_tasks": state["completed_tasks"],
        "failed_tasks": state["failed_tasks"],
        "messages": [
            HumanMessage(
                content=f"Begin implementing the current task: {current_task}"
            )
        ],
    }

    result = coder_graph.invoke(coder_input, config={"recursion_limit": 50})

    return {
        "coder_result": result["coder_result"],
        "messages": result.get("messages", []),
    }


#=================================#
#           Task Logic            #
#=================================#

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

        print(
            f"Coder completed task: {current_task}"
        )

    else:

        if current_task and current_task not in failed_tasks:
            failed_tasks.append(current_task)

        print(
            f"Coder failed task: {current_task}"
        )

    return {
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
    }