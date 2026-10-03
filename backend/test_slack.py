import asyncio
import json
import sys
from langchain_mcp_adapters.client import MultiServerMCPClient


def server(path):
    return {"command": sys.executable, "args": [path], "transport": "stdio"}


async def main():
    client = MultiServerMCPClient({
        "hr_db": server("mcp_servers/hr_db_server.py"),
        "slack": server("mcp_servers/slack_server.py"),
    })
    tools = {t.name: t for t in await client.get_tools()}
    print("Tools:", list(tools))

    # 1. DB mein request banao
    res = await tools["create_leave_request"].ainvoke({
        "employee_id": "EMP002", "leave_type": "annual",
        "start_date": "2026-10-26", "end_date": "2026-10-28",
        "reason": "Sister's wedding",
    })
    req = json.loads(res[0]["text"])
    print("\nDB:", req)
    if "error" in req:
        return

    # 2. Slack pe post karo
    post = await tools["post_leave_request"].ainvoke({
        "request_id": req["_id"],
        "employee_name": req["employee_name"],
        "leave_type": req["leave_type"],
        "start_date": req["start_date"],
        "end_date": req["end_date"],
        "working_days": req["working_days"],
        "reason": req["reason"],
        "needs_hod_approval": req["needs_hod_approval"],
    })
    print("\nSlack:", post[0]["text"])


asyncio.run(main())