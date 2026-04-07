import asyncio
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.agent import root_agent
from app.config import setup_logging

# ADK runner + services
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

APP_NAME = "multi_agent_task_orchestrator"
DEFAULT_USER = "local_user"
DEFAULT_SESSION = "local_session"

setup_logging()

# Session service + runner
session_service = InMemorySessionService()
runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=session_service)

app = FastAPI(title="Multi-Agent Task Orchestrator")


class AgentRequest(BaseModel):
    message: str


@app.on_event("startup")
async def startup_session():
    """Ensure a session exists for local calls."""
    try:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=DEFAULT_USER,
            session_id=DEFAULT_SESSION,
            state={
                "PROMPT": "",
                "prompt": "",
                "plan_notes": "",
                "execution_log": "",
                "CURRENT_DATETIME": None,  # populated at request time
            },
        )
    except Exception:
        pass


@app.get("/healthz")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/agent")
async def handle_agent(request: AgentRequest) -> dict:
    """
    Primary API entry point using ADK Runner.
    """
    # Ensure session exists (defensive in case startup hook didn't run)
    try:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=DEFAULT_USER,
            session_id=DEFAULT_SESSION,
            state={
                "PROMPT": "",
                "prompt": "",
                "plan_notes": "",
                "execution_log": "",
                "CURRENT_DATETIME": None,
            },
        )
    except Exception:
        await session_service.get_session(
            app_name=APP_NAME, user_id=DEFAULT_USER, session_id=DEFAULT_SESSION
        )

    final_text = ""
    events = []
    try:
        # Update CURRENT_DATETIME in session state for this request
        from datetime import datetime, timezone

        session = await session_service.get_session(
            app_name=APP_NAME, user_id=DEFAULT_USER, session_id=DEFAULT_SESSION
        )
        session.state["CURRENT_DATETIME"] = datetime.now(timezone.utc).isoformat()

        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=request.message)],
        )
        async for event in runner.run_async(
            user_id=DEFAULT_USER,
            session_id=DEFAULT_SESSION,
            new_message=content,
        ):
            events.append(event)
            # Extract final response text when available
            if hasattr(event, "is_final_response") and event.is_final_response():
                if getattr(event, "content", None) and getattr(event.content, "parts", None):
                    parts = event.content.parts
                    if parts and getattr(parts[0], "text", None):
                        final_text = parts[0].text
                else:
                    final_text = str(getattr(event, "content", event))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"response": final_text, "events": len(events)}
