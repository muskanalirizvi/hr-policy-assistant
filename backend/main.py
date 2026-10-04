import os
from contextlib import asynccontextmanager

import certifi
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

from agent.graph import chat
from agent.nodes import store
from agent.tools import open_sessions, close_sessions

mongo = MongoClient(os.environ["MONGODB_URI"], tlsCAFile=certifi.where())
db = mongo["acme_hr"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await open_sessions()  # MCP servers ek dafa start
    yield
    await close_sessions()
    store.client.close()
    mongo.close()


app = FastAPI(title="Acme HR Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("FRONTEND_URL", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    employee_id: str
    thread_id: str
    message: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = []
    awaiting_confirmation: bool = False


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/employees")
def employees():
    """Demo ke 'Login as' dropdown ke liye."""
    return list(db.employees.find({}, {"name": 1, "role": 1, "department": 1, "status": 1}))


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    if not db.employees.find_one({"_id": req.employee_id}, {"_id": 1}):
        raise HTTPException(status_code=404, detail="Employee not found")
    # Thread ko employee se baandho, taake ek employee ki conversation doosre mein na mile
    thread_id = f"{req.employee_id}:{req.thread_id}"
    return await chat(thread_id, req.employee_id, req.message)