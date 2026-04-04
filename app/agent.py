import logging
import os
from datetime import datetime, timedelta, timezone

import dotenv
import google.cloud.logging
from google.adk import Agent
from google.adk.agents import SequentialAgent
from google.adk.tools.tool_context import ToolContext

from app.config import get_settings, setup_logging
from app.tools import db_tools
from app.tools.mcp_tools import get_bigquery_mcp_toolset, get_maps_mcp_toolset

dotenv.load_dotenv()
setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()
model_name = settings.model


# --- Helper tool to stash user prompt in state ---
def add_prompt_to_state(tool_context: ToolContext, prompt: str) -> dict[str, str]:
    tool_context.state["PROMPT"] = prompt
    # Seed CURRENT_DATETIME if missing (UTC ISO) so agents can resolve relative times
    tool_context.state.setdefault("CURRENT_DATETIME", datetime.now(timezone.utc).isoformat())
    logger.info("[State updated] PROMPT stored.")
    return {"status": "stored"}


# --- MCP toolsets (BigQuery + Maps as in codelab) ---
maps_toolset = get_maps_mcp_toolset()
bigquery_toolset = get_bigquery_mcp_toolset()


# --- Agent definitions ---
planner_agent = Agent(
    name="planner_agent",
    model=model_name,
    description="Understands the user's request and drafts a structured action plan.",
    instruction="""
    Analyze the PROMPT and decide which tools to use:
    - Resolve relative times (e.g., "tomorrow", "next Monday") using CURRENT_DATETIME from state if present; otherwise assume current UTC now. Never ask the user for the date.
    - For tasks: create or update tasks with due dates.
    - For schedules: create events.
    - For notes/information: create notes.
    - Use Maps MCP for location reasoning; use BigQuery MCP for analytics if asked for insights.
    Save a concise plan to PLAN_NOTES and keep it in the tool context state.
    IMPORTANT: Do not greet or speak to the user. Only produce plan notes and tool calls.

    PROMPT:
    { PROMPT }
    """,
    tools=[
        maps_toolset,
        bigquery_toolset,
        db_tools.list_tasks,
        db_tools.list_events,
        db_tools.search_notes,
        db_tools.add_task,
        db_tools.create_task,
        db_tools.add_event,
        db_tools.add_note,
        db_tools.complete_task,
    ],
    output_key="plan_notes",
)


executor_agent = Agent(
    name="executor_agent",
    model=model_name,
    description="Executes the plan by calling the right tools.",
    instruction="""
    Use PLAN_NOTES to decide which actions to execute.
    Always prefer structured tool calls over free-form text.
    - add_task or create_task for new todos
    - complete_task for done items
    - add_event for calendar items (ISO8601 timestamps)
    - add_note for summaries
    Include Maps/BigQuery tools only when relevant.
    IMPORTANT: Do NOT speak to the user. If no tool calls are needed, return an empty string.

    PLAN_NOTES:
    { plan_notes }
    """,
    tools=[
        maps_toolset,
        bigquery_toolset,
        db_tools.add_task,
        db_tools.create_task,
        db_tools.complete_task,
        db_tools.add_event,
        db_tools.add_note,
    ],
    output_key="execution_log",
)


responder_agent = Agent(
    name="responder_agent",
    model=model_name,
    description="Summarizes outcomes for the user.",
    instruction="""
    Craft a concise, friendly status update based on EXECUTION_LOG and PLAN_NOTES.
    Include:
    - Tasks created/updated (ids, due dates)
    - Events scheduled
    - Notes captured
    - Any external insights (Maps/BigQuery) if present
    Keep it short and actionable.

    PLAN_NOTES:
    { plan_notes }

    EXECUTION_LOG:
    { execution_log }
    """,
)


workflow = SequentialAgent(
    name="task_manager_workflow",
    description="Coordinates planning, execution, and response.",
    sub_agents=[planner_agent, executor_agent, responder_agent],
)


root_agent = Agent(
    name="root_coordinator",
    model=model_name,
    description="Entry point agent that stores prompt then delegates to workflow.",
    instruction="""
    - If the user message is a simple greeting, thanks, or smalltalk with no task intent, reply briefly yourself and DO NOT call sub-agents.
    - Otherwise, store the raw PROMPT via add_prompt_to_state and hand off to task_manager_workflow to complete the job.
    - Only you (root) should speak to the user. Sub-agents must stay silent.
    """,
    tools=[add_prompt_to_state],
    sub_agents=[workflow],
)


def build_tool_context() -> ToolContext:
    """
    Initializes ToolContext with default state.
    """
    class _DummySession:
        def __init__(self):
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            self.state: dict = {
                "PROMPT": "",
                "PLAN_NOTES": "",
                "CURRENT_DATETIME": now,
            }

    class _DummyInvocationContext:
        def __init__(self):
            self.session = _DummySession()

    inv_ctx = _DummyInvocationContext()
    return ToolContext(invocation_context=inv_ctx)
