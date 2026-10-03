from typing import Literal
from pydantic import BaseModel, Field
from agent.llm import llm
from agent.state import AgentState


class Route(BaseModel):
    intent: Literal["policy", "my_data", "leave_request", "off_topic"] = Field(
        description="Which handler should answer the employee's message"
    )


ROUTER_PROMPT = """You route messages for Acme Corp's internal HR assistant.
Classify the employee's message into exactly one intent:

- policy: questions about company rules, policies or benefits (leave rules, remote work, allowances,
  health insurance), or general HR/employment questions. Example: "How many annual leaves do we get?"
- my_data: questions about the employee's OWN records: their remaining leave balance, role, manager,
  join date, probation status. Example: "How many annual leaves do I have left?"
- leave_request: the employee wants to apply for, request or book leave. Example: "I need leave from 19 to 21 Oct"
- off_topic: anything unrelated to work or HR. Example: "What's the weather today?"

The message may be in English, Urdu or Roman Urdu.

Message: {question}"""

router_llm = llm.with_structured_output(Route)


def router_node(state: AgentState) -> dict:
    route = router_llm.invoke(ROUTER_PROMPT.format(question=state["question"]))
    return {"intent": route.intent}


if __name__ == "__main__":
    tests = [
        ("How many annual leaves do employees get?", "policy"),
        ("How many annual leaves do I have left?", "my_data"),
        ("Can I work from Dubai for a few weeks?", "policy"),
        ("Who is my manager?", "my_data"),
        ("I want to take sick leave tomorrow", "leave_request"),
        ("meri kitni chuttiyan bachi hain?", "my_data"),
        ("mujhe 19 se 21 october ki chutti chahiye", "leave_request"),
        ("What is the legal maternity leave in Pakistan?", "policy"),
        ("Who won the cricket match yesterday?", "off_topic"),
    ]
    correct = 0
    for q, expected in tests:
        got = router_node({"question": q})["intent"]
        ok = got == expected
        correct += ok
        print(f"{'✅' if ok else '❌'} [{got:13}] {q}")
    print(f"\n{correct}/{len(tests)} correct")