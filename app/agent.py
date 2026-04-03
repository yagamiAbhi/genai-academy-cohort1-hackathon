import logging
import os
from datetime import datetime, timedelta

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
    - For tasks: create or update tasks with due dates.
    - For schedules: create events.
    - For notes/information: create notes.
    - Use Maps MCP for location reasoning; use BigQuery MCP for analytics if asked for insights.
    Save a concise plan to PLAN_NOTES and keep it in the tool context state.

    PROMPT:
    { PROMPT }
    """,
    tools=[
        maps_toolset,
        bigquery_toolset,
        db_tools.list_tasks,
        db_tools.list_events,
        db_tools.search_notes,
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
    - add_task for new todos
    - complete_task for done items
    - add_event for calendar items (ISO8601 timestamps)
    - add_note for summaries
    Include Maps/BigQuery tools only when relevant.

    PLAN_NOTES:
    { plan_notes }
    """,
    tools=[
        maps_toolset,
        bigquery_toolset,
        db_tools.add_task,
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
    - Acknowledge the user's request briefly.
    - Store the raw PROMPT via add_prompt_to_state.
    - Hand off to task_manager_workflow to complete the job.
    """,
    tools=[add_prompt_to_state],
    sub_agents=[workflow],
)


def build_tool_context() -> ToolContext:
    """
    Initializes ToolContext with default state.
    """
    ctx = ToolContext(invocation_context=None)
    ctx.state = {"PROMPT": "", "PLAN_NOTES": ""}
    return ctx
