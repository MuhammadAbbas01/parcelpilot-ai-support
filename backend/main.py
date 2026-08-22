"""
FastAPI entrypoint. Serves the chat API + the static frontend.
Mocked auth: header X-User-Role and X-User-Name stand in for a real
SSO/session layer. Swap check_auth() for real auth without touching
agent.py or the tools.
"""
from dotenv import load_dotenv
load_dotenv()  # reads ../.env for GROQ_API_KEY — must run before agent.py imports Groq

from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from models import ChatRequest, UserContext
from agent import run_agent
import insights

app = FastAPI(title="ParcelPilot Internal Ops Assistant")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SESSIONS: dict[str, list[dict]] = {}


def check_auth(x_user_role: str, x_user_name: str) -> UserContext:
    if x_user_role not in ("support_agent", "ops_manager", "admin"):
        raise HTTPException(status_code=403, detail="Unauthorised role")
    return UserContext(user_id=x_user_name, role=x_user_role, name=x_user_name)


@app.post("/api/chat")
def chat(req: ChatRequest, x_user_role: str = Header(...), x_user_name: str = Header(...)):
    user = check_auth(x_user_role, x_user_name)
    history = SESSIONS.get(req.session_id, [])
    result = run_agent(req.message, history, user)
    SESSIONS[req.session_id] = result["messages"]
    return {"reply": result["reply"], "tool_trace": result["tool_trace"]}


@app.get("/api/insights")
def get_insights(x_user_role: str = Header(...), x_user_name: str = Header(...)):
    """Proactive issue detection dashboard data. Restricted to
    ops_manager/admin — a support_agent handling one ticket at a time
    doesn't need the cross-account view, and a customer never reaches
    this endpoint at all (it's not exposed to the customer-facing tool
    surface)."""
    user = check_auth(x_user_role, x_user_name)
    if user.role not in ("ops_manager", "admin"):
        raise HTTPException(status_code=403, detail="Insights dashboard requires ops_manager or admin role")
    return insights.full_report()


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Static frontend (built as plain HTML/JS, no build step)
app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
