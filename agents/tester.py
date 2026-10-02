import os
import sys
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

sys.stdout.reconfigure(line_buffering=True)

from langchain_mistralai import ChatMistralAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

from graph.state import AgentState
from prompts.tester_prompt import TESTER_PROMPT
from tools.filesystem import list_files, read_file, write_file
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

class TestResult(BaseModel):
    passed: bool = Field(
        description="Whether all tests passed successfully."
    )
    summary: str = Field(
        description="A concise summary of the test execution results."
    )
    tests_run: int = Field(
        default=0,
        description="Total number of tests executed."
    )
    tests_passed: int = Field(
        default=0,
        description="Number of tests that passed."
    )
    tests_failed: int = Field(
        default=0,
        description="Number of tests that failed or errored."
    )
    failures: List[str] = Field(
        default_factory=list,
        description="Details of any failed tests or error tracebacks."
    )

test_result_llm = llm.with_structured_output(TestResult)

# =========================================================
# TOOLS
# =========================================================

tester_tools = [
    list_files,
    read_file,
    write_file,
    run_command,
]

tool_map = {t.name: t for t in tester_tools}
tester_llm = llm.bind_tools(tester_tools)


# =========================================================
# TESTER AGENT
# =========================================================

def tester_agent(state: AgentState):
    print("\n================ TESTER AGENT ================")
    current_task = state.get("current_task", "Run and verify project tests.")
    print(f"Task: {current_task}")

    system_prompt = f"""
{TESTER_PROMPT}

==================================================
PROJECT CONTEXT
==================================================

USER REQUEST:
{state.get("user_request", "")}

COMPLETED IMPLEMENTATION TASKS:
{state.get("completed_tasks", [])}

CURRENT TESTING TASK:
{current_task}
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Begin testing the project for task: {current_task}"),
    ]

    history_records = []

    # Run tool-calling execution loop (up to 5 turns)
    for turn in range(5):
        response = tester_llm.invoke(messages)
        messages.append(response)

        tool_calls = getattr(response, "tool_calls", [])
        if not tool_calls:
            break

        tool_names = [tc.get("name") for tc in tool_calls]
        print(f"[Tester] Turn {turn + 1}: Executing tool(s): {tool_names}")

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

            # Truncate large tool output to save tokens
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
Analyze the test execution history and provide the structured test result.

CURRENT TASK:
{current_task}

EXECUTION LOG:
{chr(10).join(history_records) if history_records else "No external commands executed."}

Determine whether the tests passed, the number of tests run/passed/failed, and any failure tracebacks.
"""

    result = test_result_llm.invoke(finalize_prompt)

    completed_tasks = list(state.get("completed_tasks", []))
    failed_tasks = list(state.get("failed_tasks", []))

    if result.passed:
        print(f"[Tester] Result: PASSED - {result.summary}")
        if current_task and current_task not in completed_tasks:
            completed_tasks.append(current_task)
        failed_tasks = []
    else:
        print(f"[Tester] Result: FAILED - {result.summary}")
        if current_task and current_task not in failed_tasks:
            failed_tasks.append(current_task)
        if result.failures:
            print(f"[Tester] Failures detected: {len(result.failures)}")

    print("==============================================\n")

    return {
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "test_result": result.model_dump(),
    }
