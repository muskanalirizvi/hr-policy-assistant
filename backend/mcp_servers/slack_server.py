import os
import ssl
import certifi
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

ssl_ctx = ssl.create_default_context(cafile=certifi.where())
slack = WebClient(token=os.environ["SLACK_BOT_TOKEN"], ssl=ssl_ctx)
CHANNEL = os.environ["SLACK_CHANNEL_ID"]

mcp = FastMCP("acme-slack")


@mcp.tool()
def post_leave_request(
    request_id: str,
    employee_name: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    working_days: int,
    reason: str = "",
    needs_hod_approval: bool = False,
) -> dict:
    """Post a saved leave request to the HR Slack channel for review."""
    lines = [
        f":memo: *New leave request* `{request_id}`",
        f"*Employee:* {employee_name}",
        f"*Type:* {leave_type.capitalize()} leave",
        f"*Dates:* {start_date} → {end_date} ({working_days} working days)",
    ]
    if reason:
        lines.append(f"*Reason:* {reason}")
    if needs_hod_approval:
        lines.append(":warning: Over 10 working days, needs Head of Department approval")

    try:
        resp = slack.chat_postMessage(channel=CHANNEL, text="\n".join(lines))
        return {"posted": True, "ts": resp["ts"]}
    except SlackApiError as e:
        return {"posted": False, "error": e.response["error"]}


if __name__ == "__main__":
    mcp.run()