from typing import TypedDict, List


class AgentState(TypedDict):

    user_request: str

    plan: List[str]

    architecture: str

    current_task: str

    completed_tasks: List[str]

    failed_tasks: List[str]

    test_results: str

    code_review: str

    next_agent: str

    manager_reason: str

    final_response: str