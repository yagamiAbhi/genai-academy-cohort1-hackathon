from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.adk.tools.tool_context import ToolContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Event, Note, SessionLocal, Task

logger = logging.getLogger(__name__)


def _get_session() -> Session:
    return SessionLocal()


def add_task(
    tool_context: ToolContext,
    title: str,
    due: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a task and store in DB."""
    session = _get_session()
    try:
        due_dt = datetime.fromisoformat(due) if due else None
        task = Task(title=title, due=due_dt, notes=notes)
        session.add(task)
        session.commit()
        session.refresh(task)
        tool_context.state.setdefault("TASK_IDS", []).append(task.id)
        logger.info("Task created with id %s", task.id)
        return {"id": task.id, "status": "created"}
    finally:
        session.close()


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
    session = _get_session()
    try:
        stmt = select(Task)
        if status:
            stmt = stmt.where(Task.status == status)
        tasks = session.scalars(stmt.order_by(Task.due.nulls_last(), Task.created_at)).all()
        return [
            {
                "id": t.id,
                "title": t.title,
                "due": t.due.isoformat() if t.due else None,
                "status": t.status,
                "notes": t.notes,
            }
            for t in tasks
        ]
    finally:
        session.close()


def complete_task(tool_context: ToolContext, task_id: int) -> Dict[str, Any]:
    """Mark a task as completed."""
    session = _get_session()
    try:
        task = session.get(Task, task_id)
        if not task:
            return {"status": "not_found", "id": task_id}
        task.status = "done"
        session.commit()
        return {"status": "done", "id": task_id}
    finally:
        session.close()


def add_event(
    tool_context: ToolContext,
    title: str,
    start: str,
    end: str,
    location: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a calendar event."""
    session = _get_session()
    try:
        event = Event(
            title=title,
            start=datetime.fromisoformat(start),
            end=datetime.fromisoformat(end),
            location=location,
            description=description,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        tool_context.state.setdefault("EVENT_IDS", []).append(event.id)
        return {"id": event.id, "status": "created"}
    finally:
        session.close()


def list_events(tool_context: ToolContext, after: Optional[str] = None) -> List[Dict[str, Any]]:
    """List events, optionally after a given ISO datetime."""
    session = _get_session()
    try:
        stmt = select(Event)
        if after:
            stmt = stmt.where(Event.start >= datetime.fromisoformat(after))
        events = session.scalars(stmt.order_by(Event.start)).all()
        return [
            {
                "id": e.id,
                "title": e.title,
                "start": e.start.isoformat(),
                "end": e.end.isoformat(),
                "location": e.location,
                "description": e.description,
            }
            for e in events
        ]
    finally:
        session.close()


def add_note(tool_context: ToolContext, title: str, content: str) -> Dict[str, Any]:
    """Create a note."""
    session = _get_session()
    try:
        note = Note(title=title, content=content)
        session.add(note)
        session.commit()
        session.refresh(note)
        tool_context.state.setdefault("NOTE_IDS", []).append(note.id)
        return {"id": note.id, "status": "created"}
    finally:
        session.close()


def search_notes(tool_context: ToolContext, query: str) -> List[Dict[str, Any]]:
    """Simple substring search over note title/content."""
    session = _get_session()
    try:
        q = f"%{query.lower()}%"
        stmt = select(Note).where(
            (Note.title.ilike(q)) | (Note.content.ilike(q))
        )
        notes = session.scalars(stmt.order_by(Note.updated_at.desc())).all()
        return [
            {"id": n.id, "title": n.title, "content": n.content, "updated_at": n.updated_at.isoformat()}
            for n in notes
        ]
    finally:
        session.close()
