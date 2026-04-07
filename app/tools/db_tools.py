from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.adk.tools.tool_context import ToolContext
from google.cloud import bigquery

from app.models import DATASET, PROJECT, ensure_tables, get_bq_client

logger = logging.getLogger(__name__)


ensure_tables()
client = get_bq_client()


def _next_id(table: str) -> int:
    query = f"SELECT IFNULL(MAX(id), 0) + 1 AS next_id FROM `{PROJECT}.{DATASET}.{table}`"
    result = client.query(query).result()
    for row in result:
        return int(row.next_id or 1)
    return 1


def add_task(
    tool_context: ToolContext,
    title: str,
    due: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a task and store in BigQuery."""
    task_id = _next_id("tasks")
    now = datetime.utcnow()
    row = {
        "id": task_id,
        "title": title,
        "due": due,
        "status": "open",
        "notes": notes,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    errors = client.insert_rows_json(f"{PROJECT}.{DATASET}.tasks", [row])
    if errors:
        return {"status": "error", "errors": errors}
    tool_context.state.setdefault("TASK_IDS", []).append(task_id)
    logger.info("Task created with id %s", task_id)
    return {"id": task_id, "status": "created"}


# Alias to align with common tool name
def create_task(
    tool_context: ToolContext,
    title: str,
    due: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    return add_task(tool_context=tool_context, title=title, due=due, notes=notes)


def list_tasks(tool_context: ToolContext, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List tasks, optionally filtered by status."""
    where = "WHERE status = @status" if status else ""
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("status", "STRING", status)]
        if status
        else []
    )
    query = f"""
        SELECT id, title, due, status, notes, created_at, updated_at
        FROM `{PROJECT}.{DATASET}.tasks`
        {where}
        ORDER BY due NULLS LAST, created_at
    """
    rows = client.query(query, job_config=job_config).result()
    return [
        {
            "id": r.id,
            "title": r.title,
            "due": r.due.isoformat() if r.due else None,
            "status": r.status,
            "notes": r.notes,
        }
        for r in rows
    ]


def complete_task(tool_context: ToolContext, task_id: int) -> Dict[str, Any]:
    """Mark a task as completed."""
    query = f"""
        UPDATE `{PROJECT}.{DATASET}.tasks`
        SET status = 'done', updated_at = CURRENT_TIMESTAMP()
        WHERE id = @id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("id", "INT64", task_id)]
    )
    res = client.query(query, job_config=job_config).result()
    if res.num_dml_affected_rows == 0:
        return {"status": "not_found", "id": task_id}
    return {"status": "done", "id": task_id}


def add_event(
    tool_context: ToolContext,
    title: str,
    start: str,
    end: str,
    location: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a calendar event."""
    event_id = _next_id("events")
    now = datetime.utcnow()
    row = {
        "id": event_id,
        "title": title,
        "start": start,
        "end": end,
        "location": location,
        "description": description,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    errors = client.insert_rows_json(f"{PROJECT}.{DATASET}.events", [row])
    if errors:
        return {"status": "error", "errors": errors}
    tool_context.state.setdefault("EVENT_IDS", []).append(event_id)
    return {"id": event_id, "status": "created"}


def list_events(tool_context: ToolContext, after: Optional[str] = None) -> List[Dict[str, Any]]:
    """List events, optionally after a given ISO datetime."""
    where = "WHERE start >= @after" if after else ""
    params = [bigquery.ScalarQueryParameter("after", "TIMESTAMP", after)] if after else []
    query = f"""
        SELECT id, title, start, end, location, description
        FROM `{PROJECT}.{DATASET}.events`
        {where}
        ORDER BY start
    """
    rows = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=params)).result()
    return [
        {
            "id": r.id,
            "title": r.title,
            "start": r.start.isoformat() if r.start else None,
            "end": r.end.isoformat() if r.end else None,
            "location": r.location,
            "description": r.description,
        }
        for r in rows
    ]


def add_note(tool_context: ToolContext, title: str, content: str) -> Dict[str, Any]:
    """Create a note."""
    note_id = _next_id("notes")
    now = datetime.utcnow()
    row = {
        "id": note_id,
        "title": title,
        "content": content,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    errors = client.insert_rows_json(f"{PROJECT}.{DATASET}.notes", [row])
    if errors:
        return {"status": "error", "errors": errors}
    tool_context.state.setdefault("NOTE_IDS", []).append(note_id)
    return {"id": note_id, "status": "created"}


def search_notes(tool_context: ToolContext, query: str) -> List[Dict[str, Any]]:
    """Simple substring search over note title/content."""
    query_sql = f"""
        SELECT id, title, content, updated_at
        FROM `{PROJECT}.{DATASET}.notes`
        WHERE LOWER(title) LIKE '%' || LOWER(@q) || '%'
           OR LOWER(content) LIKE '%' || LOWER(@q) || '%'
        ORDER BY updated_at DESC
    """
    params = [bigquery.ScalarQueryParameter("q", "STRING", query)]
    rows = client.query(query_sql, job_config=bigquery.QueryJobConfig(query_parameters=params)).result()
    return [
        {
            "id": r.id,
            "title": r.title,
            "content": r.content,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]
