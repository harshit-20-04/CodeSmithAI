from typing import Annotated, List, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class CoderState(TypedDict, total=False):

    user_request: str

    plan: List[str]

    architecture: dict

    current_task: str

    completed_tasks: List[str]

    failed_tasks: List[str]

    messages: Annotated[
        List[BaseMessage],
        add_messages
    ]

    coder_result: dict