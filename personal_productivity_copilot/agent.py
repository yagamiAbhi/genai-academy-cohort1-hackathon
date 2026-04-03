from google.adk.agents import LlmAgent, SequentialAgent

from .config import APP_NAME, MODEL_NAME
from .prompts import (
    PLANNER_INSTRUCTION,
    SCHEDULER_INSTRUCTION,
    TASK_INSTRUCTION,
    NOTES_INSTRUCTION,
)
from .schemas.models import (
    NoteRecord,
    PlanRecord,
    TaskRecord,
    UserProfile,
    WorkflowRunRecord,
)
from .tools.firestore_memory import (
    upsert_user_profile,
    save_task,
    save_note,
    save_plan,
    save_workflow_run,
    update_workflow_run,
    list_user_tasks,
    list_user_notes,
)
from .tools.mcp_toolsets import (
    build_calendar_toolset,
    build_task_toolset,
    build_notes_toolset,
)


def create_or_update_user_profile(
    user_id: str,
    name: str = "",
    timezone: str = "Asia/Kolkata",
) -> dict:
    """
    Create or update a user profile in Firestore.

    Args:
        user_id (str): Unique user identifier.
        name (str): User display name.
        timezone (str): User timezone.

    Returns:
        dict: Status and stored profile data.
    """
    profile = UserProfile(
        user_id=user_id,
        name=name or None,
        timezone=timezone,
    )
    return upsert_user_profile(profile)


def store_task_in_firestore(
    user_id: str,
    title: str,
    description: str = "",
    priority: str = "medium",
    status: str = "pending",
    due_date: str = "",
) -> dict:
    """
    Store a task record in Firestore.

    Args:
        user_id (str): User ID.
        title (str): Task title.
        description (str): Task details.
        priority (str): low, medium, high.
        status (str): pending, in_progress, completed.
        due_date (str): Due date or datetime in string form.

    Returns:
        dict: Status and saved task metadata.
    """
    task = TaskRecord(
        user_id=user_id,
        title=title,
        description=description or None,
        priority=priority,
        status=status,
        due_date=due_date or None,
    )
    return save_task(task)


def store_note_in_firestore(
    user_id: str,
    title: str,
    content: str,
    tags: list[str] | None = None,
) -> dict:
    """
    Store a note record in Firestore.

    Args:
        user_id (str): User ID.
        title (str): Note title.
        content (str): Note content.
        tags (list[str] | None): Optional tags.

    Returns:
        dict: Status and saved note metadata.
    """
    note = NoteRecord(
        user_id=user_id,
        title=title,
        content=content,
        tags=tags or [],
    )
    return save_note(note)


def save_execution_plan(
    user_id: str,
    raw_request: str,
    planner_output: str,
    scheduler_output: str = "",
    task_output: str = "",
    final_output: str = "",
) -> dict:
    """
    Save the workflow plan and outputs in Firestore.

    Args:
        user_id (str): User ID.
        raw_request (str): Original user message.
        planner_output (str): Planner agent output.
        scheduler_output (str): Scheduler agent output.
        task_output (str): Task agent output.
        final_output (str): Final workflow output.

    Returns:
        dict: Status and saved plan metadata.
    """
    plan = PlanRecord(
        user_id=user_id,
        raw_request=raw_request,
        planner_output=planner_output,
        scheduler_output=scheduler_output or None,
        task_output=task_output or None,
        final_output=final_output or None,
    )
    return save_plan(plan)


def create_workflow_log(
    user_id: str,
    session_id: str,
    status: str,
) -> dict:
    """
    Create a workflow execution log entry.

    Args:
        user_id (str): User ID.
        session_id (str): Session identifier.
        status (str): Workflow status.

    Returns:
        dict: Status and workflow run metadata.
    """
    run = WorkflowRunRecord(
        user_id=user_id,
        session_id=session_id,
        status=status,
        step_results={},
    )
    return save_workflow_run(run)


def update_workflow_status(
    workflow_run_id: str,
    status: str,
    step_results: dict | None = None,
) -> dict:
    """
    Update a workflow run with latest status and step outputs.

    Args:
        workflow_run_id (str): Workflow run document ID.
        status (str): Current status.
        step_results (dict | None): Agent outputs.

    Returns:
        dict: Update status.
    """
    updates = {
        "status": status,
        "step_results": step_results or {},
    }
    return update_workflow_run(workflow_run_id, updates)


calendar_toolset = build_calendar_toolset()
task_toolset = build_task_toolset()
notes_toolset = build_notes_toolset()


planner_agent = LlmAgent(
    name="PlannerAgent",
    model=MODEL_NAME,
    description="Breaks a user productivity request into a structured execution plan.",
    instruction=PLANNER_INSTRUCTION + """
Additional rules:
- Always identify whether the request needs calendar actions, task actions, note actions, or all three.
- Always produce a clear execution order.
- If user identity is missing, assume the client application will provide a user_id separately.
- Keep output structured and concise.
""",
    tools=[
        create_or_update_user_profile,
        create_workflow_log,
        list_user_tasks,
        list_user_notes,
    ],
    output_key="planner_output",
)


scheduler_agent = LlmAgent(
    name="SchedulerAgent",
    model=MODEL_NAME,
    description="Handles scheduling and calendar operations from the planner output.",
    instruction=SCHEDULER_INSTRUCTION + """
Additional rules:
- Only perform calendar-related work.
- Use calendar MCP tools when calendar operations are needed.
- Do not create tasks or notes here.
- Return structured output for later agents.
""",
    tools=[calendar_toolset],
    output_key="scheduler_output",
)


task_agent = LlmAgent(
    name="TaskAgent",
    model=MODEL_NAME,
    description="Handles task creation and task updates based on plan and schedule.",
    instruction=TASK_INSTRUCTION + """
Additional rules:
- Only perform task-related work.
- Use task MCP tools for task manager actions.
- Use Firestore tool storage when tasks need to be persisted as structured records.
- Keep output structured for the Notes Agent.
""",
    tools=[
        task_toolset,
        store_task_in_firestore,
        list_user_tasks,
    ],
    output_key="task_output",
)


notes_agent = LlmAgent(
    name="NotesAgent",
    model=MODEL_NAME,
    description="Stores notes, saves the workflow result, and prepares the final user response.",
    instruction=NOTES_INSTRUCTION + """
Additional rules:
- Save useful notes and summary context when appropriate.
- Save the consolidated workflow result in Firestore.
- Final response must clearly state what was planned, scheduled, created, and saved.
- If any action could not be completed, mention it under pending issues.
""",
    tools=[
        notes_toolset,
        store_note_in_firestore,
        save_execution_plan,
    ],
    output_key="final_output",
)


root_agent = SequentialAgent(
    name='personal_productivity_copilot',
    description="Personal Productivity Copilot using a sequential ADK workflow.",
    sub_agents=[
        planner_agent,
        scheduler_agent,
        task_agent,
        notes_agent,
    ],
)