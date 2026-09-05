# ruff: noqa: B008
from __future__ import annotations

import uuid

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from aurora.core import settings
from aurora.importers import (
    import_chatgpt_export,
    import_claude_export,
    import_gemini_export,
    import_generic_conversation,
)
from apps.api.workspace_routes import router as workspace_router

router = APIRouter(tags=["imports"])
bearer = HTTPBearer(auto_error=False)


class ConversationImportRequest(BaseModel):
    workspace_id: uuid.UUID
    provider: str = Field(pattern="^(chatgpt|claude|gemini|generic)$")
    source_name: str = Field(default="Imported conversation", min_length=1, max_length=500)
    payload: dict | list[dict]


def _user(credentials: HTTPAuthorizationCredentials | None) -> uuid.UUID:
    from apps.api.main import current_user

    return current_user(credentials)


@router.post("/conversations/import")
def import_conversation(
    request: ConversationImportRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    user_id = _user(credentials)
    if not settings.database_url:
        raise HTTPException(503, "DATABASE_URL is not configured")
    if request.provider == "chatgpt":
        messages = import_chatgpt_export(request.payload, request.source_name)
    elif request.provider == "claude":
        messages = import_claude_export(request.payload, request.source_name)
    elif request.provider == "gemini":
        messages = import_gemini_export(request.payload, request.source_name)
    else:
        if not isinstance(request.payload, list):
            raise HTTPException(422, "Generic conversation payload must be a list")
        messages = import_generic_conversation(request.payload, request.source_name)
    if not messages:
        raise HTTPException(422, "No importable messages found")

    session_id = uuid.uuid4()
    source_id = uuid.uuid4()
    with psycopg.connect(settings.database_url) as conn:
        if not conn.execute(
            "select 1 from public.workspace_members where workspace_id=%s and user_id=%s",
            (request.workspace_id, user_id),
        ).fetchone():
            raise HTTPException(403, "User is not a member of this workspace")
        conn.execute(
            "insert into public.sources(id,workspace_id,source_type,name,provider,metadata) values (%s,%s,'model',%s,%s,%s::jsonb)",
            (source_id, request.workspace_id, request.source_name, request.provider, '{"import":true}'),
        )
        conn.execute(
            "insert into public.sessions(id,workspace_id,user_id,title,metadata) values (%s,%s,%s,%s,%s::jsonb)",
            (session_id, request.workspace_id, user_id, request.source_name[:500], '{"imported":true}'),
        )
        for sequence_no, message in enumerate(messages, start=1):
            event_id = uuid.uuid4()
            conn.execute(
                "insert into public.events(id,workspace_id,session_id,event_type,producer_type,event_time,recorded_at,correlation_id,payload) values (%s,%s,%s,'conversation.imported','integration',coalesce(%s,now()),now(),%s,%s::jsonb)",
                (event_id, request.workspace_id, session_id, message.created_at, session_id, '{"provider":"' + request.provider + '"}'),
            )
            conn.execute(
                "insert into public.messages(workspace_id,session_id,event_id,role,content,source_id,sequence_no,created_at) values (%s,%s,%s,%s,%s,%s,%s,coalesce(%s,now()))",
                (request.workspace_id, session_id, event_id, message.role, message.content, source_id, sequence_no, message.created_at),
            )
        conn.commit()
    return {
        "session_id": str(session_id),
        "source_id": str(source_id),
        "provider": request.provider,
        "messages_imported": len(messages),
        "model_text_is_historical_context": True,
        "claims_promoted_to_fact": False,
    }


router.include_router(workspace_router)
