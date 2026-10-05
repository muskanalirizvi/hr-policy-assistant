import json
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
import os

SERVERS_DIR = Path(__file__).resolve().parent.parent / "mcp_servers"


def _server(filename):
    return {
        "command": sys.executable,
        "args": [str(SERVERS_DIR / filename)],
        "transport": "stdio",
        "env": dict(os.environ),  # Render pe MCP servers ko bhi env variables chahiye
    }

_tools = None
_stack = None


async def open_sessions():
    """FastAPI start hone pe: dono MCP servers ek dafa chalu karo aur khule rakho."""
    global _tools, _stack
    _stack = AsyncExitStack()
    _tools = {}
    for name in ["hr_db", "slack"]:
        session = await _stack.enter_async_context(client.session(name))
        for tool in await load_mcp_tools(session):
            _tools[tool.name] = tool


async def close_sessions():
    global _tools, _stack
    if _stack:
        await _stack.aclose()
    _tools, _stack = None, None


async def call_tool(name: str, args: dict) -> dict:
    global _tools
    if _tools is None:  # scripts (jaise graph.py test) mein: har call pe naya session
        _tools = {t.name: t for t in await client.get_tools()}
    result = await _tools[name].ainvoke(args)
    return json.loads(result[0]["text"])