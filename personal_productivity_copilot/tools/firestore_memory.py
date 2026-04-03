from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import firebase_admin
from firebase_admin import credentials, firestore

from ..config import (
    FIRESTORE_USERS_COLLECTION,
    FIRESTORE_TASKS_COLLECTION,
    FIRESTORE_NOTES_COLLECTION,
    FIRESTORE_PLANS_COLLECTION,
    FIRESTORE_WORKFLOW_RUNS_COLLECTION,
)
from ..schemas.models import (
    NoteRecord,
    PlanRecord,
    TaskRecord,
    UserProfile,
    WorkflowRunRecord,
)


def _get_or_init_firebase_app():
    try:
        return firebase_admin.get_app()
    except ValueError:
        cred = credentials.ApplicationDefault()
        return firebase_admin.initialize_app(cred)


def get_firestore_client():
    _get_or_init_firebase_app()
    return firestore.client()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_user_profile(profile: UserProfile) -> Dict[str, Any]:
    db = get_firestore_client()
    doc_ref = db.collection(FIRESTORE_USERS_COLLECTION).document(profile.user_id)

    payload = profile.model_dump()
    payload["updated_at"] = utc_now_iso()

    existing = doc_ref.get()
    if not existing.exists:
        payload["created_at"] = utc_now_iso()

    doc_ref.set(payload, merge=True)
    return {"status": "success", "user_id": profile.user_id, "data": payload}


def save_task(task: TaskRecord) -> Dict[str, Any]:
    db = get_firestore_client()
    doc_ref = db.collection(FIRESTORE_TASKS_COLLECTION).document()

    payload = task.model_dump()
    payload["created_at"] = utc_now_iso()
    payload["updated_at"] = utc_now_iso()

    doc_ref.set(payload)
    return {"status": "success", "task_id": doc_ref.id, "data": payload}


def save_note(note: NoteRecord) -> Dict[str, Any]:
    db = get_firestore_client()
    doc_ref = db.collection(FIRESTORE_NOTES_COLLECTION).document()

    payload = note.model_dump()
    payload["created_at"] = utc_now_iso()
    payload["updated_at"] = utc_now_iso()

    doc_ref.set(payload)
    return {"status": "success", "note_id": doc_ref.id, "data": payload}


def save_plan(plan: PlanRecord) -> Dict[str, Any]:
    db = get_firestore_client()
    doc_ref = db.collection(FIRESTORE_PLANS_COLLECTION).document()

    payload = plan.model_dump()
    payload["created_at"] = utc_now_iso()
    payload["updated_at"] = utc_now_iso()

    doc_ref.set(payload)
    return {"status": "success", "plan_id": doc_ref.id, "data": payload}


def save_workflow_run(run: WorkflowRunRecord) -> Dict[str, Any]:
    db = get_firestore_client()
    doc_ref = db.collection(FIRESTORE_WORKFLOW_RUNS_COLLECTION).document()

    payload = run.model_dump()
    payload["created_at"] = utc_now_iso()
    payload["updated_at"] = utc_now_iso()

    doc_ref.set(payload)
    return {"status": "success", "workflow_run_id": doc_ref.id, "data": payload}


def update_workflow_run(run_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    db = get_firestore_client()
    doc_ref = db.collection(FIRESTORE_WORKFLOW_RUNS_COLLECTION).document(run_id)

    updates["updated_at"] = utc_now_iso()
    doc_ref.set(updates, merge=True)
    return {"status": "success", "workflow_run_id": run_id, "updates": updates}


def list_user_tasks(user_id: str, status: Optional[str] = None) -> Dict[str, Any]:
    db = get_firestore_client()
    query = db.collection(FIRESTORE_TASKS_COLLECTION).where("user_id", "==", user_id)

    if status:
        query = query.where("status", "==", status)

    docs = query.stream()
    tasks: List[Dict[str, Any]] = []

    for doc in docs:
        item = doc.to_dict()
        item["task_id"] = doc.id
        tasks.append(item)

    return {"status": "success", "count": len(tasks), "tasks": tasks}


def list_user_notes(user_id: str) -> Dict[str, Any]:
    db = get_firestore_client()
    query = db.collection(FIRESTORE_NOTES_COLLECTION).where("user_id", "==", user_id)

    docs = query.stream()
    notes: List[Dict[str, Any]] = []

    for doc in docs:
        item = doc.to_dict()
        item["note_id"] = doc.id
        notes.append(item)

    return {"status": "success", "count": len(notes), "notes": notes}