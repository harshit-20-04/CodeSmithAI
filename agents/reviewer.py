import os
import sys
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

sys.stdout.reconfigure(line_buffering=True)

from langchain_mistralai import ChatMistralAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

from graph.state import AgentState
from prompts.reviewer_prompt import REVIEWER_PROMPT
from tools.filesystem import list_files, read_file

load_dotenv()

# =========================================================
# LLM
# =========================================================

llm = ChatMistralAI(
    model="codestral-latest",
    temperature=0,
)

# =========================================================
# STRUCTURED OUTPUT SCHEMA
# =========================================================

class ReviewResult(BaseModel):
    approved: bool = Field(
        description="Whether the code implementation is approved for production."
    )
    score: int = Field(
        ge=1,
        le=10,
        description="Overall quality score from 1 (poor) to 10 (excellent)."
    )
    summary: str = Field(
        description="High-level summary of the code review findings."
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="List of strengths in the implementation."
    )
    issues: List[str] = Field(
        default_factory=list,
        description="List of issues, defects, or security concerns found."
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Actionable recommendations for improvement."
    )

reviewer_result_llm = llm.with_structured_output(ReviewResult)

# =========================================================
# TOOLS
# =========================================================

reviewer_tools = [
    list_files,
    read_file,
]

tool_map = {t.name: t for t in reviewer_tools}
reviewer_llm = llm.bind_tools(reviewer_tools)


# =========================================================
# REVIEWER AGENT
# =========================================================

def reviewer_agent(state: AgentState):
    print("\n================ REVIEWER AGENT ================")
    current_task = state.get("current_task", "Review codebase quality and completeness.")
    print(f"Task: {current_task}")

    system_prompt = f"""
{REVIEWER_PROMPT}

==================================================
PROJECT CONTEXT
==================================================

USER REQUEST:
{state.get("user_request", "")}

DEVELOPMENT PLAN:
{state.get("plan", [])}

ARCHITECTURE:
{state.get("architecture", "")}

COMPLETED TASKS:
{state.get("completed_tasks", [])}
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Inspect the workspace files and perform the code review."),
    ]

    history_records = []

    # Run inspection loop (up to 4 turns)
    for turn in range(4):
        response = reviewer_llm.invoke(messages)
        messages.append(response)

        tool_calls = getattr(response, "tool_calls", [])
        if not tool_calls:
            break

        tool_names = [tc.get("name") for tc in tool_calls]
        print(f"[Reviewer] Turn {turn + 1}: Inspecting via tool(s): {tool_names}")

        for tc in tool_calls:
            tool_name = tc.get("name")
            tool_args = tc.get("args", {})
            call_id = tc.get("id")

            tool_fn = tool_map.get(tool_name)
            if tool_fn:
                try:
                    tool_output = tool_fn.invoke(tool_args)
                except Exception as e:
                    tool_output = f"Tool inspection error: {str(e)}"
            else:
                tool_output = f"Unknown tool: {tool_name}"

            truncated_output = str(tool_output)
            if len(truncated_output) > 600:
                truncated_output = f"{truncated_output[:300]}\n... [truncated] ...\n{truncated_output[-300:]}"

            history_records.append(f"Tool {tool_name}({tool_args}) -> {truncated_output}")
            messages.append(
                ToolMessage(
                    content=truncated_output,
                    tool_call_id=call_id
                )
            )

    finalize_prompt = f"""
Based on your inspection of the codebase, produce the structured ReviewResult.

INSPECTION LOG:
{chr(10).join(history_records) if history_records else "Workspace files inspected."}

Evaluate whether the code is approved, score out of 10, list strengths, issues, and recommendations.
"""

    result = reviewer_result_llm.invoke(finalize_prompt)

    completed_tasks = list(state.get("completed_tasks", []))
    if result.approved:
        print(f"[Reviewer] Status: APPROVED (Score: {result.score}/10)")
        if current_task and current_task not in completed_tasks:
            completed_tasks.append(current_task)
    else:
        print(f"[Reviewer] Status: CHANGES REQUESTED (Score: {result.score}/10)")
        if result.issues:
            print(f"[Reviewer] Key issues: {result.issues}")

    print(f"[Reviewer] Summary: {result.summary}")
    print("================================================\n")

    return {
        "completed_tasks": completed_tasks,
        "review_result": result.model_dump(),
    }
