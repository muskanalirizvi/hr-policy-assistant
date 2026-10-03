from typing import Literal, TypedDict

Intent = Literal["policy", "my_data", "leave_request", "off_topic"]


class AgentState(TypedDict, total=False):
    question: str
    employee_id: str  # UI se aata hai, LLM se nahi
    intent: Intent
    answer: str
    sources: list[str]