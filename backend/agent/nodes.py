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
from langgraph.types import interrupt

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
    reset = {"answer": None, "sources": [], "confirmed": False}
    if state.get("awaiting_leave"):
        return {**reset, "intent": "leave_request"}
    route = router_llm.invoke(ROUTER_PROMPT.format(question=state["question"]))
    return {**reset, "intent": route.intent}


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
    new = {k: v for k, v in d.model_dump().items() if v}
    # Agar pichle message mein kuch details aa chuki thi, unhe saath milao
    prev = (state.get("leave") or {}) if state.get("awaiting_leave") else {}
    leave = {**prev, **new}
    if leave.get("start_date") and not leave.get("end_date"):
        leave["end_date"] = leave["start_date"]

    missing = []
    if not leave.get("leave_type"):
        missing.append("the leave type (annual, sick or casual)")
    if not leave.get("start_date"):
        missing.append("the dates")
    if missing:
        return {"leave": leave, "awaiting_leave": True,
                "answer": f"Sure, I can help with that. Please tell me {' and '.join(missing)}."}
    return {"leave": leave, "awaiting_leave": False, "answer": None}


def _leave_args(state: AgentState) -> dict:
    l = state["leave"]
    return {
        "employee_id": state["employee_id"],  # state se, LLM se nahi
        "leave_type": l["leave_type"],
        "start_date": l["start_date"],
        "end_date": l["end_date"],
        "reason": l.get("reason") or "",
    }


async def leave_validate_node(state: AgentState) -> dict:
    preview = await call_tool("create_leave_request", {**_leave_args(state), "dry_run": True})
    if "error" in preview:
        return {"answer": f"I can't submit this request: {preview['error']}", "leave": {}}
    return {"leave_preview": preview}

def days_text(n) -> str:
    return f"{n} working day" + ("" if n == 1 else "s")

YES_WORDS = {"yes", "y", "haan", "han", "ha", "ji", "jee", "ok", "okay", "sure", "confirm", "submit"}


def confirm_node(state: AgentState) -> dict:
    p = state["leave_preview"]
    summary = (
        "Please confirm your leave request:\n"
        f"• Type: {p['leave_type'].capitalize()} leave\n"
        f"• Dates: {p['start_date']} → {p['end_date']} ({days_text(p['working_days'])})\n"
        f"• Reason: {p['reason'] or '-'}\n"
    )
    if p.get("needs_hod_approval"):
        summary += "• Note: over 10 working days, needs Head of Department approval\n"
    summary += "\nShall I submit it? (yes / no)"

    reply = interrupt(summary)  # ⏸ graph yahan rukta hai, user ke jawab ka intezaar

    words = str(reply).lower().replace(",", " ").split()
    if any(w in YES_WORDS for w in words):
        return {"confirmed": True}
    return {"confirmed": False, "leave": {}, "answer": "Okay, I've cancelled it. Nothing was submitted."}


async def submit_leave_node(state: AgentState) -> dict:
    req = await call_tool("create_leave_request", _leave_args(state))
    if "error" in req:
        return {"answer": f"I couldn't submit your request: {req['error']}", "leave": {}}

    post = await call_tool("post_leave_request", {
        "request_id": req["_id"],
        "employee_name": req["employee_name"],
        "leave_type": req["leave_type"],
        "start_date": req["start_date"],
        "end_date": req["end_date"],
        "working_days": req["working_days"],
        "reason": req["reason"],
        "needs_hod_approval": req["needs_hod_approval"],
    })
    note = ("HR has been notified on Slack." if post.get("posted")
            else "It's saved, but I couldn't notify HR on Slack. Please let them know directly.")
    answer = (f"✅ Submitted! Your {req['leave_type']} leave request `{req['_id']}` "
              f"({req['start_date']} → {req['end_date']}, {days_text(req['working_days'])}) is pending review. {note}")
    return {"answer": answer, "leave": {}}

# ---------- Off topic ----------
OFF_TOPIC_REPLY = (
    "I'm Acme Corp's HR assistant, so I can only help with company policies, "
    "your HR records and leave requests. Is there anything HR-related I can help with?"
)


def off_topic_node(state: AgentState) -> dict:
    return {"answer": OFF_TOPIC_REPLY, "sources": []}

