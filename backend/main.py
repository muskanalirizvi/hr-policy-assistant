import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import bcrypt
import certifi
import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from pymongo import MongoClient

from agent.graph import chat
from agent.nodes import store
from agent.tools import open_sessions, close_sessions

load_dotenv()

JWT_SECRET = os.environ["JWT_SECRET"]
TOKEN_HOURS = 8
PUBLIC_FIELDS = {"name": 1, "email": 1, "role": 1, "department": 1, "status": 1}

mongo = MongoClient(os.environ["MONGODB_URI"], tlsCAFile=certifi.where())
db = mongo["acme_hr"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await open_sessions()
    yield
    await close_sessions()
    store.client.close()
    mongo.close()


app = FastAPI(title="Acme HR Assistant", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("FRONTEND_URL", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


def public(emp: dict) -> dict:
    """Frontend ko sirf ye fields jaati hain. password_hash kabhi nahi."""
    return {
        "id": emp["_id"], "name": emp["name"], "email": emp["email"],
        "role": emp["role"], "department": emp["department"], "status": emp["status"],
    }


# ---------- Auth ----------
class LoginRequest(BaseModel):
    email: str
    password: str


bearer = HTTPBearer()


def current_employee_id(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    """Har protected request pe: token verify karo aur usme se employee_id nikalo."""
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Session expired, please sign in again")
    return payload["sub"]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/demo-accounts")
def demo_accounts():
    """Login page pe demo accounts dikhane ke liye."""
    return [public(e) for e in db.employees.find({}, PUBLIC_FIELDS)]


@app.post("/login")
def login(req: LoginRequest):
    emp = db.employees.find_one({"email": req.email.strip().lower()})
    if not emp or not bcrypt.checkpw(req.password.encode(), emp["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = jwt.encode(
        {"sub": emp["_id"], "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)},
        JWT_SECRET,
        algorithm="HS256",
    )
    return {"token": token, "employee": public(emp)}


@app.get("/me")
def me(employee_id: str = Depends(current_employee_id)):
    emp = db.employees.find_one({"_id": employee_id}, PUBLIC_FIELDS)
    if not emp:
        raise HTTPException(status_code=401, detail="Account not found")
    return public(emp)


# ---------- Chat ----------
class ChatRequest(BaseModel):
    thread_id: str
    message: str  # employee_id ab request mein nahi hai


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = []
    awaiting_confirmation: bool = False


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest, employee_id: str = Depends(current_employee_id)):
    thread_id = f"{employee_id}:{req.thread_id}"
    return await chat(thread_id, employee_id, req.message)