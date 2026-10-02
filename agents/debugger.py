import os
import sys
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

sys.stdout.reconfigure(line_buffering=True)

from langchain_mistralai import ChatMistralAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

from graph.state import AgentState
from prompts.debugger_prompt import DEBUGGER_PROMPT
from tools.filesystem import list_files, read_file, edit_file, write_file
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
# STRUCTURED OUTPUT SCHEMA
# =========================================================

class DebuggerResult(BaseModel):
    fixed: bool = Field(
        description="Whether the bug or failure was successfully resolved."
    )
    summary: str = Field(
        description="A concise explanation of the debugging actions taken."
    )
    root_cause: str = Field(
        description="The identified root cause of the error."
    )
    modified_files: List[str] = Field(
        default_factory=list,
        description="Files edited or updated to fix the issue."
    )
    unresolved_errors: List[str] = Field(
        default_factory=list,
        description="Any remaining errors if the issue could not be resolved."
    )

debugger_result_llm = llm.with_structured_output(DebuggerResult)

# =========================================================
# TOOLS
# =========================================================

debugger_tools = [
    list_files,
    read_file,
    edit_file,
    write_file,
    run_command,
]

tool_map = {t.name: t for t in debugger_tools}
debugger_llm = llm.bind_tools(debugger_tools)


# =========================================================
# DEBUGGER AGENT
# =========================================================

def debugger_agent(state: AgentState):
    print("\n================ DEBUGGER AGENT ================")
    current_task = state.get("current_task", "Diagnose and fix errors.")
    print(f"Task: {current_task}")

    test_result = state.get("test_result", {})
    coder_result = state.get("coder_result", {})
    failed_tasks = list(state.get("failed_tasks", []))

    error_context = ""
    if test_result.get("failures"):
        error_context += f"Test Failures:\n" + "\n".join(test_result["failures"]) + "\n"
    if coder_result.get("errors"):
        error_context += f"Coder Errors:\n" + "\n".join(coder_result["errors"]) + "\n"

    system_prompt = f"""
{DEBUGGER_PROMPT}

==================================================
ERROR CONTEXT
==================================================

FAILED TASKS:
{failed_tasks}

DETECTED FAILURES / ERRORS:
{error_context if error_context else "Inspect workspace and tests for errors."}

CURRENT DEBUGGING TASK:
{current_task}
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Investigate and fix the errors for: {current_task}"),
    ]

    history_records = []

    # Run tool-calling execution loop (up to 5 turns)
    for turn in range(5):
        response = debugger_llm.invoke(messages)
        messages.append(response)

        tool_calls = getattr(response, "tool_calls", [])
        if not tool_calls:
            break

        tool_names = [tc.get("name") for tc in tool_calls]
        print(f"[Debugger] Turn {turn + 1}: Executing tool(s): {tool_names}")

        for tc in tool_calls:
            tool_name = tc.get("name")
            tool_args = tc.get("args", {})
            call_id = tc.get("id")

            tool_fn = tool_map.get(tool_name)
            if tool_fn:
                try:
                    tool_output = tool_fn.invoke(tool_args)
                except Exception as e:
                    tool_output = f"Tool execution error: {str(e)}"
            else:
                tool_output = f"Unknown tool: {tool_name}"

            truncated_output = str(tool_output)
            if len(truncated_output) > 800:
                truncated_output = f"{truncated_output[:400]}\n... [truncated] ...\n{truncated_output[-400:]}"

            history_records.append(f"Tool {tool_name}({tool_args}) -> {truncated_output}")
            messages.append(
                ToolMessage(
                    content=truncated_output,
                    tool_call_id=call_id
                )
            )

    # Structured result finalization
    finalize_prompt = f"""
Analyze the debugging execution history and report the result.

CURRENT TASK:
{current_task}

DEBUGGING LOG:
{chr(10).join(history_records) if history_records else "No file modifications were made."}

Return whether the issue was fixed, root cause, modified files, and any remaining errors.
"""

    result = debugger_result_llm.invoke(finalize_prompt)

    if result.fixed:
        print(f"[Debugger] Status: FIXED - {result.summary}")
        print(f"[Debugger] Root cause: {result.root_cause}")
        failed_tasks = []
    else:
        print(f"[Debugger] Status: UNRESOLVED - {result.summary}")
        if current_task and current_task not in failed_tasks:
            failed_tasks.append(current_task)

    print("================================================\n")

    return {
        "failed_tasks": failed_tasks,
        "debug_result": result.model_dump(),
    }
