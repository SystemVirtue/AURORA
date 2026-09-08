"""Read-only Knowledge Explorer API for the AURORA MVP."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

router = APIRouter(prefix="/v1/knowledge", tags=["knowledge"])
bearer = HTTPBearer(auto_error=False)


class KnowledgeItem(BaseModel):
    id: str
    type: str
    title: str
    status: str | None = None
    confidence: float | None = None
    excerpt: str | None = None


def _db():
    from aurora.core import get_connection
    return get_connection()


def _user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):  # noqa: B008
    from apps.api.main import current_user
    return current_user(credentials)


def _member(conn, workspace_id: str, user_id: str) -> bool:
    row = conn.execute(
        "select 1 from workspace_members where workspace_id=%s and user_id=%s limit 1",
        (workspace_id, user_id),
    ).fetchone()
    return bool(row)


@router.get("/search", response_model=list[KnowledgeItem])
def search_knowledge(
    workspace_id: str = Query(...),
    q: str = Query(""),
    kind: str = Query("all"),
    limit: int = Query(50, ge=1, le=100),
    user=Depends(_user),  # noqa: B008
):
    if kind not in {"all", "claims", "documents"}:
        raise HTTPException(status_code=400, detail="kind must be all, claims, or documents")
    conn = _db()
    try:
        if not _member(conn, workspace_id, user["sub"]):
            raise HTTPException(status_code=403, detail="workspace membership required")
        term = q.strip()
        out: list[KnowledgeItem] = []
        if kind in ("all", "claims"):
            rows = conn.execute(
                """select id::text, subject, predicate, object, assertion_status, confidence, excerpt
                   from claims where workspace_id=%s
                   and (%s='' or to_tsvector('simple', coalesce(subject,'')||' '||coalesce(predicate,'')||' '||coalesce(object,'')||' '||coalesce(excerpt,'')) @@ plainto_tsquery('simple',%s))
                   order by updated_at desc nulls last, id desc limit %s""",
                (workspace_id, term, term, limit),
            ).fetchall()
            out.extend(KnowledgeItem(id=r[0], type="claim", title=f"{r[1]} {r[2]} {r[3]}", status=r[4], confidence=float(r[5]) if r[5] is not None else None, excerpt=r[6]) for r in rows)
        if kind in ("all", "documents") and len(out) < limit:
            rows = conn.execute(
                """select id::text, title from documents where workspace_id=%s
                   and (%s='' or title ilike %s) order by created_at desc, id desc limit %s""",
                (workspace_id, term, f"%{term}%", limit - len(out)),
            ).fetchall()
            out.extend(KnowledgeItem(id=r[0], type="document", title=r[1] or "Untitled document") for r in rows)
        return out[:limit]
    finally:
        conn.close()
