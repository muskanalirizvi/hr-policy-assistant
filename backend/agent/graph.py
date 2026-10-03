import asyncio
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from agent.state import AgentState
from agent.nodes import (
    store, router_node, policy_node, web_node, my_data_node, off_topic_node,
    leave_extract_node, leave_validate_node, confirm_node, submit_leave_node,
)

builder = StateGraph(AgentState)
builder.add_node("router", router_node)
builder.add_node("policy", policy_node)
builder.add_node("web", web_node)
builder.add_node("my_data", my_data_node)
builder.add_node("off_topic", off_topic_node)
builder.add_node("leave_extract", leave_extract_node)
builder.add_node("leave_validate", leave_validate_node)
builder.add_node("confirm", confirm_node)
builder.add_node("submit", submit_leave_node)

builder.add_edge(START, "router")
builder.add_conditional_edges("router", lambda s: s["intent"], {
    "policy": "policy",
    "my_data": "my_data",
    "leave_request": "leave_extract",
    "off_topic": "off_topic",
})
builder.add_conditional_edges("policy", lambda s: "web" if s.get("answer") is None else END)
builder.add_conditional_edges("leave_extract", lambda s: END if s.get("answer") else "leave_validate")
builder.add_conditional_edges("leave_validate", lambda s: END if s.get("answer") else "confirm")
builder.add_conditional_edges("confirm", lambda s: "submit" if s.get("confirmed") else END)
for node in ["web", "my_data", "off_topic", "submit"]:
    builder.add_edge(node, END)

graph = builder.compile(checkpointer=InMemorySaver())


async def chat(thread_id: str, employee_id: str, message: str):
    """Ek user message bhejo, agent ka jawab aur sources wapas lo."""
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = await graph.aget_state(config)

    if snapshot.next:  # graph confirmation pe ruka hua hai → user ka jawab resume karo
        result = await graph.ainvoke(Command(resume=message), config)
    else:
        result = await graph.ainvoke({"question": message, "employee_id": employee_id}, config)

    if "__interrupt__" in result:  # graph ruk gaya, confirmation maang raha hai
        return result["__interrupt__"][0].value, []
    return result.get("answer"), result.get("sources", [])


# ---------- Test: poori conversations ----------
async def run(thread_id, employee_id, messages):
    print(f"\n{'=' * 15} {employee_id} {'=' * 15}")
    for m in messages:
        answer, sources = await chat(thread_id, employee_id, m)
        print(f"\n👤 {m}\n🤖 {answer}")
        if sources:
            print("   📎", sources)


async def main():
    # Ayesha: balance → leave request (type missing) → type batao → confirm → submit
    await run("t1", "EMP001", [
        "How many annual leaves do I have left?",
        "I need leave from 19 to 21 October for a family trip",
        "annual",
        "yes",
    ])
    # Sara: casual leave → confirmation pe "no"
    await run("t2", "EMP003", [
        "I want casual leave on 26 October",
        "no",
    ])
    # Sara: probation mein annual → confirm se pehle hi error
    await run("t3", "EMP003", [
        "I need annual leave from 26 to 27 October",
    ])
    store.client.close()


if __name__ == "__main__":
    asyncio.run(main())