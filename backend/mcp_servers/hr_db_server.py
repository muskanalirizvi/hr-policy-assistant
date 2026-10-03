import os
import certifi
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pymongo import MongoClient

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


if __name__ == "__main__":
    mcp.run()  # stdio transport: agent isse subprocess ki tarah chalayega