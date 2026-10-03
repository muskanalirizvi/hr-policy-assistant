import json
import sys
from pathlib import Path
from langchain_mcp_adapters.client import MultiServerMCPClient

SERVERS_DIR = Path(__file__).resolve().parent.parent / "mcp_servers"


def _server(filename):
    return {"command": sys.executable, "args": [str(SERVERS_DIR / filename)], "transport": "stdio"}


client = MultiServerMCPClient({
    "hr_db": _server("hr_db_server.py"),
    "slack": _server("slack_server.py"),
})

_tools = None


async def call_tool(name: str, args: dict) -> dict:
    global _tools
    if _tools is None:
        _tools = {t.name: t for t in await client.get_tools()}
    result = await _tools[name].ainvoke(args)
    return json.loads(result[0]["text"])