import asyncio
from datetime import date
from typing import Literal, Optional
from pydantic import BaseModel, Field

from agent.llm import llm, to_text
from agent.state import AgentState
from agent.tools import call_tool
from agent.web_search import web_answer
from rag.answer import answer as rag_answer
from rag.retriever import get_vector_store

store = get_vector_store()


# ---------- Router ----------
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


# ---------- Policy (RAG) + Web ----------
def policy_node(state: AgentState) -> dict:
    text, docs = rag_answer(store, state["question"])
    if text is None:
        return {"answer": None}  # graph isse web_node pe bhejega
    # Top chunk hamesha, baaki sirf strong matches
    shown = [docs[0]] + [d for d in docs[1:] if d.metadata["rerank_score"] >= 0.5]
    sources = [f"{d.metadata['source']} → {d.metadata.get('section', '')}" for d in shown]
    return {"answer": text, "sources": sources}


def web_node(state: AgentState) -> dict:
    text, sources = web_answer(state["question"])
    return {"answer": text, "sources": sources}


# ---------- My data (MCP) ----------
MY_DATA_PROMPT = """You are Acme Corp's HR assistant. Answer the employee's question using ONLY their records below.
Be concise and friendly. If the employee's status is "probation", mention that annual leave cannot be used until probation ends. Reply in the same language as the question (English, Urdu or Roman Urdu).

Employee records:
{records}

Question: {question}"""


async def my_data_node(state: AgentState) -> dict:
    eid = state["employee_id"]
    profile = await call_tool("get_employee_profile", {"employee_id": eid})
    if "error" in profile:
        return {"answer": "I couldn't find your employee record. Please contact HR.", "sources": []}
    balance = await call_tool("get_leave_balance", {"employee_id": eid})

    records = {**profile, **balance}
    resp = await llm.ainvoke(MY_DATA_PROMPT.format(records=records, question=state["question"]))
    return {"answer": to_text(resp.content).strip(), "sources": []}


# ---------- Leave request: extraction ----------
class LeaveDetails(BaseModel):
    leave_type: Optional[Literal["annual", "sick", "casual"]] = None
    start_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    reason: Optional[str] = None


EXTRACT_PROMPT = """Extract leave request details from the employee's message.
Today is {today} ({weekday}). Convert relative dates like "tomorrow" or "next Monday" to YYYY-MM-DD.

Rules:
- leave_type must be annual, sick or casual. A generic word like "leave" or "chutti" does not tell the type: leave it empty.
- If only one day is mentioned, start_date and end_date are the same.
- Leave a field empty if the employee didn't say it. Do not guess.
- "next <weekday>" / "agle <weekday>" means the nearest upcoming one after today.

Message: {question}"""

extract_llm = llm.with_structured_output(LeaveDetails)


async def leave_extract_node(state: AgentState) -> dict:
    today = date.today()
    d = await extract_llm.ainvoke(EXTRACT_PROMPT.format(
        today=today.isoformat(), weekday=today.strftime("%A"), question=state["question"]
    ))
    if d.start_date and not d.end_date:
        d.end_date = d.start_date

    missing = []
    if not d.leave_type:
        missing.append("the leave type (annual, sick or casual)")
    if not d.start_date:
        missing.append("the dates")
    if missing:
        return {"leave": d.model_dump(), "answer": f"Sure, I can help with that. Please tell me {' and '.join(missing)}."}
    return {"leave": d.model_dump(), "answer": None}  # sab mil gaya → confirm step (6c)


# ---------- Off topic ----------
OFF_TOPIC_REPLY = (
    "I'm Acme Corp's HR assistant, so I can only help with company policies, "
    "your HR records and leave requests. Is there anything HR-related I can help with?"
)


def off_topic_node(state: AgentState) -> dict:
    return {"answer": OFF_TOPIC_REPLY, "sources": []}


# ---------- Test ----------
async def main():
    base = {"employee_id": "EMP003"}  # Sara, probation

    print("\n=== policy ===")
    print(policy_node({**base, "question": "Can I take annual leave during probation?"}))

    print("\n=== policy → web fallback ===")
    q = "What is the legal maternity leave in Pakistan?"
    r = policy_node({**base, "question": q})
    print("policy answer:", r["answer"])
    if r["answer"] is None:
        print(web_node({**base, "question": q})["answer"])

    print("\n=== my_data (Roman Urdu) ===")
    print((await my_data_node({**base, "question": "meri kitni chuttiyan bachi hain?"}))["answer"])

    print("\n=== leave_extract (complete) ===")
    print(await leave_extract_node({**base, "question": "I need annual leave from 19 to 21 October for a family trip"}))

    print("\n=== leave_extract (missing type) ===")
    print(await leave_extract_node({**base, "question": "mujhe agle Monday chutti chahiye"}))

    print("\n=== off_topic ===")
    print(off_topic_node(base)["answer"])

    store.client.close()


if __name__ == "__main__":
    asyncio.run(main())