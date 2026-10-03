import os
import certifi
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pymongo import MongoClient
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

load_dotenv()

client = MongoClient(os.environ["MONGODB_URI"], tlsCAFile=certifi.where())
db = client["acme_hr"]

mcp = FastMCP("acme-hr-db")


@mcp.tool()
def get_employee_profile(employee_id: str) -> dict:
    """Get an employee's profile: name, department, role, manager, join date, probation status and work mode."""
    emp = db.employees.find_one({"_id": employee_id}, {"leave_balance": 0})
    if not emp:
        return {"error": f"Employee {employee_id} not found"}
    return emp


@mcp.tool()
def get_leave_balance(employee_id: str) -> dict:
    """Get an employee's remaining leave balance (annual, sick, casual) and probation status."""
    emp = db.employees.find_one(
        {"_id": employee_id}, {"name": 1, "status": 1, "leave_balance": 1}
    )
    if not emp:
        return {"error": f"Employee {employee_id} not found"}
    return emp

LEAVE_TYPES = {"annual", "sick", "casual"}
NOTICE_DAYS = 7  # Leave Policy, 5. How to Apply


def working_days(start: date, end: date) -> int:
    days, d = 0, start
    while d <= end:
        if d.weekday() < 5:  # Mon-Fri
            days += 1
        d += timedelta(days=1)
    return days


@mcp.tool()
def create_leave_request(
    employee_id: str, leave_type: str, start_date: str, end_date: str, reason: str = "", dry_run: bool = False
) -> dict:
    """Create a leave request after checking it against Acme Corp leave policy.
    leave_type must be annual, sick or casual. Dates must be in YYYY-MM-DD format.
    With dry_run=True, only validates and returns the preview without saving."""
    emp = db.employees.find_one({"_id": employee_id})
    if not emp:
        return {"error": f"Employee {employee_id} not found"}

    leave_type = leave_type.lower().strip()
    if leave_type not in LEAVE_TYPES:
        return {"error": f"Invalid leave type '{leave_type}'. Use annual, sick or casual."}

    try:
        start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    except ValueError:
        return {"error": "Dates must be in YYYY-MM-DD format."}
    if end < start:
        return {"error": "End date cannot be before start date."}

    days = working_days(start, end)
    if days == 0:
        return {"error": "The selected dates contain no working days."}

    # Policy checks
    if leave_type == "annual" and emp["status"] == "probation":
        return {"error": "Employees on probation cannot take annual leave (Leave Policy, 1. Annual Leave)."}
    if leave_type != "sick" and (start - date.today()).days < NOTICE_DAYS:
        return {"error": f"Leave must be requested at least {NOTICE_DAYS} days in advance (Leave Policy, 5. How to Apply)."}

    balance = emp["leave_balance"][leave_type]
    if days > balance:
        return {"error": f"Not enough {leave_type} leave: requested {days} days, balance is {balance}."}

    request = {
        "_id": f"LR-{uuid4().hex[:6].upper()}",
        "employee_id": employee_id,
        "employee_name": emp["name"],
        "manager": emp["manager"],
        "leave_type": leave_type,
        "start_date": start_date,
        "end_date": end_date,
        "working_days": days,
        "reason": reason,
        "status": "pending",
        "needs_hod_approval": days > 10,  # Leave Policy, 5. How to Apply
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if dry_run:
        return request
    db.leave_requests.insert_one(request)
    return request


if __name__ == "__main__":
    mcp.run()  # stdio transport: agent isse subprocess ki tarah chalayega