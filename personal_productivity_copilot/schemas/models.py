from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    user_id: str
    name: Optional[str] = None
    timezone: str = "Asia/Kolkata"
    preferences: Dict[str, Any] = Field(default_factory=dict)


class TaskRecord(BaseModel):
    user_id: str
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    status: str = "pending"
    due_date: Optional[str] = None
    source: str = "agent"


class NoteRecord(BaseModel):
    user_id: str
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)
    linked_task_ids: List[str] = Field(default_factory=list)


class PlanRecord(BaseModel):
    user_id: str
    raw_request: str
    planner_output: str
    scheduler_output: Optional[str] = None
    task_output: Optional[str] = None
    final_output: Optional[str] = None


class WorkflowRunRecord(BaseModel):
    user_id: str
    session_id: str
    status: str
    step_results: Dict[str, Any] = Field(default_factory=dict)