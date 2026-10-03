import asyncio
import sys
from langchain_mcp_adapters.client import MultiServerMCPClient


async def main():
    client = MultiServerMCPClient({
        "hr_db": {
            "command": sys.executable,
            "args": ["mcp_servers/hr_db_server.py"],
            "transport": "stdio",
        }
    })

    tools = {t.name: t for t in await client.get_tools()}
    print("Tools:", list(tools))
    create = tools["create_leave_request"]

    cases = [
        ("Valid request (Ayesha, 3 din)",
         {"employee_id": "EMP001", "leave_type": "annual", "start_date": "2026-10-19", "end_date": "2026-10-21", "reason": "Family trip"}),
        ("Probation (Sara, annual)",
         {"employee_id": "EMP003", "leave_type": "annual", "start_date": "2026-10-19", "end_date": "2026-10-20"}),
        ("Balance kam (Usman, 5 din, balance 2)",
         {"employee_id": "EMP004", "leave_type": "annual", "start_date": "2026-10-19", "end_date": "2026-10-23"}),
        ("Notice kam (Ayesha, kal ki casual)",
         {"employee_id": "EMP001", "leave_type": "casual", "start_date": "2026-10-06", "end_date": "2026-10-06"}),
    ]

    for label, args in cases:
        result = await create.ainvoke(args)
        print(f"\n{label}:\n  {result[0]['text']}")


asyncio.run(main())