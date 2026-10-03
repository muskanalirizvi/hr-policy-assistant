from typing import Literal, TypedDict

Intent = Literal["policy", "my_data", "leave_request", "off_topic"]


class AgentState(TypedDict, total=False):
    question: str
    employee_id: str        # UI se aata hai, LLM se nahi
    intent: Intent
    answer: str | None
    sources: list[str]
    leave: dict             # ab tak nikali hui leave details
    awaiting_leave: bool    # kya hum user se missing details ka intezaar kar rahe hain?
    leave_preview: dict     # dry_run ka result, confirmation mein dikhta hai
    confirmed: bool