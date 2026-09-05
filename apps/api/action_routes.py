from __future__ import annotations

import uuid

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aurora.core import settings

router = APIRouter(prefix="/v1", tags=["actions"])


def _current_user():
    # Imported lazily to avoid a circular import with apps.api.main.
    from apps.api.main import current_user

    return current_user


class GoalCreate(BaseModel):
    workspace_id: uuid.UUID
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    priority: int = Field(default=0, ge=-100, le=100)


class GoalUpdate(BaseModel):
    workspace_id: uuid.UUID
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    status: str | None = None
    priority: int | None = Field(default=None, ge=-100, le=100)


class TaskCreate(BaseModel):
    workspace_id: uuid.UUID
    goal_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    priority: int = Field(default=0, ge=-100, le=100)
    due_at: str | None = None


class TaskUpdate(BaseModel):
    workspace_id: uuid.UUID
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    status: str | None = None
    priority: int | None = Field(default=None, ge=-100, le=100)
    goal_id: uuid.UUID | None = None
    due_at: str | None = None


class DecisionCreate(BaseModel):
    workspace_id: uuid.UUID
    title: str = Field(min_length=1, max_length=500)
    decision: str = Field(min_length=1, max_length=10000)
    rationale: str | None = Field(default=None, max_length=10000)
    confidence: float | None = Field(default=None, ge=0, le=1)


def _access(conn, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
    if not conn.execute(
        "select 1 from public.workspace_members where workspace_id=%s and user_id=%s",
        (workspace_id, user_id),
    ).fetchone():
        raise HTTPException(403, "User is not a member of this workspace")


def _row(row) -> dict:
    return {"id": str(row[0]), **row[1]}


@router.get("/goals")
def list_goals(workspace_id: uuid.UUID, user_id: uuid.UUID = Depends(_current_user())) -> dict:
    with psycopg.connect(settings.database_url) as conn:
        _access(conn, workspace_id, user_id)
        rows = conn.execute(
            "select id,title,description,status,priority,created_at,updated_at from public.goals where workspace_id=%s order by priority desc, created_at",
            (workspace_id,),
        ).fetchall()
    keys = ("title", "description", "status", "priority", "created_at", "updated_at")
    return {"goals": [_row((r[0], dict(zip(keys, r[1:])))) for r in rows]}


@router.post("/goals")
def create_goal(request: GoalCreate, user_id: uuid.UUID = Depends(_current_user())) -> dict:
    with psycopg.connect(settings.database_url) as conn:
        _access(conn, request.workspace_id, user_id)
        row = conn.execute(
            "insert into public.goals(workspace_id,title,description,priority) values (%s,%s,%s,%s) returning id,created_at,updated_at",
            (request.workspace_id, request.title, request.description, request.priority),
        ).fetchone()
        conn.commit()
    return {"goal_id": str(row[0]), "created_at": row[1], "updated_at": row[2]}


@router.patch("/goals/{goal_id}")
def update_goal(goal_id: uuid.UUID, request: GoalUpdate, user_id: uuid.UUID = Depends(_current_user())) -> dict:
    allowed = {"active", "paused", "completed", "cancelled"}
    if request.status is not None and request.status not in allowed:
        raise HTTPException(422, "Invalid goal status")
    fields, values = [], []
    for name in ("title", "description", "status", "priority"):
        value = getattr(request, name)
        if value is not None:
            fields.append(f"{name}=%s")
            values.append(value)
    if not fields:
        raise HTTPException(422, "No goal fields supplied")
    fields.append("updated_at=now()")
    values.extend([goal_id, request.workspace_id])
    with psycopg.connect(settings.database_url) as conn:
        _access(conn, request.workspace_id, user_id)
        result = conn.execute(f"update public.goals set {', '.join(fields)} where id=%s and workspace_id=%s", values)
        if result.rowcount != 1:
            raise HTTPException(404, "Goal not found")
        conn.commit()
    return {"goal_id": str(goal_id), "updated": True}


@router.get("/tasks")
def list_tasks(workspace_id: uuid.UUID, status: str | None = None, user_id: uuid.UUID = Depends(_current_user())) -> dict:
    with psycopg.connect(settings.database_url) as conn:
        _access(conn, workspace_id, user_id)
        if status:
            rows = conn.execute("select id,goal_id,title,description,status,priority,due_at,created_at,updated_at from public.tasks where workspace_id=%s and status=%s order by priority desc, created_at", (workspace_id, status)).fetchall()
        else:
            rows = conn.execute("select id,goal_id,title,description,status,priority,due_at,created_at,updated_at from public.tasks where workspace_id=%s order by priority desc, created_at", (workspace_id,)).fetchall()
    keys = ("goal_id", "title", "description", "status", "priority", "due_at", "created_at", "updated_at")
    tasks = []
    for r in rows:
        item = dict(zip(keys, r[1:])); item["id"] = str(r[0]); item["goal_id"] = str(item["goal_id"]) if item["goal_id"] else None; tasks.append(item)
    return {"tasks": tasks}


@router.post("/tasks")
def create_task(request: TaskCreate, user_id: uuid.UUID = Depends(_current_user())) -> dict:
    with psycopg.connect(settings.database_url) as conn:
        _access(conn, request.workspace_id, user_id)
        if request.goal_id and not conn.execute("select 1 from public.goals where id=%s and workspace_id=%s", (request.goal_id, request.workspace_id)).fetchone():
            raise HTTPException(422, "Goal does not belong to this workspace")
        row = conn.execute("insert into public.tasks(workspace_id,goal_id,title,description,priority,due_at) values (%s,%s,%s,%s,%s,%s) returning id,created_at,updated_at", (request.workspace_id, request.goal_id, request.title, request.description, request.priority, request.due_at)).fetchone()
        conn.commit()
    return {"task_id": str(row[0]), "created_at": row[1], "updated_at": row[2]}


@router.patch("/tasks/{task_id}")
def update_task(task_id: uuid.UUID, request: TaskUpdate, user_id: uuid.UUID = Depends(_current_user())) -> dict:
    allowed = {"open", "in_progress", "blocked", "completed", "cancelled"}
    if request.status is not None and request.status not in allowed:
        raise HTTPException(422, "Invalid task status")
    with psycopg.connect(settings.database_url) as conn:
        _access(conn, request.workspace_id, user_id)
        if request.goal_id and not conn.execute("select 1 from public.goals where id=%s and workspace_id=%s", (request.goal_id, request.workspace_id)).fetchone():
            raise HTTPException(422, "Goal does not belong to this workspace")
        fields, values = [], []
        for name in ("title", "description", "status", "priority", "goal_id", "due_at"):
            value = getattr(request, name)
            if value is not None:
                fields.append(f"{name}=%s"); values.append(value)
        if not fields: raise HTTPException(422, "No task fields supplied")
        fields.append("updated_at=now()"); values.extend([task_id, request.workspace_id])
        result = conn.execute(f"update public.tasks set {', '.join(fields)} where id=%s and workspace_id=%s", values)
        if result.rowcount != 1: raise HTTPException(404, "Task not found")
        conn.commit()
    return {"task_id": str(task_id), "updated": True}


@router.post("/decisions")
def create_decision(request: DecisionCreate, user_id: uuid.UUID = Depends(_current_user())) -> dict:
    with psycopg.connect(settings.database_url) as conn:
        _access(conn, request.workspace_id, user_id)
        row = conn.execute("insert into public.decisions(workspace_id,title,decision,rationale,confidence) values (%s,%s,%s,%s,%s) returning id,created_at", (request.workspace_id, request.title, request.decision, request.rationale, request.confidence)).fetchone()
        conn.commit()
    return {"decision_id": str(row[0]), "created_at": row[1]}


@router.get("/decisions")
def list_decisions(workspace_id: uuid.UUID, user_id: uuid.UUID = Depends(_current_user())) -> dict:
    with psycopg.connect(settings.database_url) as conn:
        _access(conn, workspace_id, user_id)
        rows = conn.execute("select id,title,decision,rationale,confidence,created_at from public.decisions where workspace_id=%s order by created_at desc", (workspace_id,)).fetchall()
    keys = ("title", "decision", "rationale", "confidence", "created_at")
    return {"decisions": [{"id": str(r[0]), **dict(zip(keys, r[1:]))} for r in rows]}
