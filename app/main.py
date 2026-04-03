from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.agent import build_tool_context, root_agent
from app.config import setup_logging
from app.models import init_db

setup_logging()
init_db()

app = FastAPI(title="Multi-Agent Task Orchestrator")


class AgentRequest(BaseModel):
    message: str


@app.get("/healthz")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/agent")
def handle_agent(request: AgentRequest) -> dict:
    """
    Primary API entry point.
    """
    ctx = build_tool_context()
    try:
        response = root_agent.run(request.message, tool_context=ctx)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"response": response, "state": ctx.state}

