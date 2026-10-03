import asyncio
import sys
from langchain_mcp_adapters.client import MultiServerMCPClient


async def main():
    client = MultiServerMCPClient({
        "hr_db": {
            "command": sys.executable,  # venv wala python
            "args": ["mcp_servers/hr_db_server.py"],
            "transport": "stdio",
        }
    })

    tools = {t.name: t for t in await client.get_tools()}
    print("Tools:", list(tools))

    print("\nEMP003 leave balance:")
    print(await tools["get_leave_balance"].ainvoke({"employee_id": "EMP003"}))

    print("\nEMP001 profile:")
    print(await tools["get_employee_profile"].ainvoke({"employee_id": "EMP001"}))

    print("\nGalat ID (EMP999):")
    print(await tools["get_leave_balance"].ainvoke({"employee_id": "EMP999"}))


asyncio.run(main())