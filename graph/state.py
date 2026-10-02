from typing import Annotated, List, TypedDict, Union
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):

    user_request: str

    plan: List[str]

    architecture: Union[dict, str]

    current_task: str

    completed_tasks: List[str]

    failed_tasks: List[str]

    next_agent: str

    manager_reason: str

    final_response: str

    coder_result: dict

    test_result: dict

    debug_result: dict

    review_result: dict

    messages: Annotated[
        List[BaseMessage],
        add_messages
    ]