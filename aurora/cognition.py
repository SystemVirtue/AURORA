from __future__ import annotations

import hashlib
import re
import uuid
from typing import Any

import psycopg

from .core import event_envelope


def chunk_text(text: str, max_chars: int = 2400) -> list[str]:
    """Deterministically split text on paragraph/sentence boundaries before hard cuts."""
    cleaned = re.sub(r"\r\n?", "\n", text).strip()
    if not cleaned:
        return []
    paragraphs = re.split(r"\n\s*\n", cleaned)
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        while len(paragraph) > max_chars:
            cut = paragraph.rfind(" ", 0, max_chars)
            cut = cut if cut > max_chars // 2 else max_chars
            chunks.append(paragraph[:cut].strip())
            paragraph = paragraph[cut:].strip()
        current = paragraph
    if current:
        chunks.append(current)
    return chunks


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def create_source_and_document(
    conn: psycopg.Connection,
    *,
    workspace_id: uuid.UUID,
    name: str,
    content: str,
    mime_type: str = "text/plain",
) -> tuple[uuid.UUID, uuid.UUID]:
    source_id = uuid.uuid4()
    document_id = uuid.uuid4()
    conn.execute(
        "insert into public.sources (id,workspace_id,source_type,name,metadata) values (%s,%s,'document',%s,%s::jsonb)",
        (source_id, workspace_id, name, '{"ingestion":"api"}'),
    )
    conn.execute(
        """insert into public.documents
           (id,workspace_id,source_id,name,mime_type,content,content_hash)
           values (%s,%s,%s,%s,%s,%s,%s)""",
        (document_id, workspace_id, source_id, name, mime_type, content, content_hash(content)),
    )
    for index, chunk in enumerate(chunk_text(content)):
        conn.execute(
            """insert into public.document_chunks
               (workspace_id,document_id,chunk_index,content,content_hash,token_estimate)
               values (%s,%s,%s,%s,%s,%s)""",
            (workspace_id, document_id, index, chunk, content_hash(chunk), max(1, len(chunk) // 4)),
        )
    return source_id, document_id


def retrieve_lexical(
    conn: psycopg.Connection,
    *,
    workspace_id: uuid.UUID,
    question: str,
    limit: int = 8,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """select dc.id, dc.document_id, d.name, dc.chunk_index, dc.content,
                  ts_rank_cd(to_tsvector('simple', dc.content), plainto_tsquery('simple', %s)) as score
           from public.document_chunks dc
           join public.documents d on d.id = dc.document_id
          where dc.workspace_id = %s
            and to_tsvector('simple', dc.content) @@ plainto_tsquery('simple', %s)
          order by score desc, dc.created_at desc
          limit %s""",
        (question, workspace_id, question, limit),
    ).fetchall()
    return [
        {"chunk_id": row[0], "document_id": row[1], "document": row[2], "chunk_index": row[3], "content": row[4], "score": float(row[5])}
        for row in rows
    ]


def record_message(
    conn: psycopg.Connection,
    *,
    workspace_id: uuid.UUID,
    session_id: uuid.UUID,
    role: str,
    content: str,
    source_id: uuid.UUID | None,
    correlation_id: uuid.UUID,
    causation_id: uuid.UUID | None = None,
) -> tuple[uuid.UUID, uuid.UUID]:
    event = event_envelope(
        event_type=f"message.{role}",
        producer_type="human" if role == "user" else "model",
        workspace_id=str(workspace_id),
        session_id=str(session_id),
        correlation_id=str(correlation_id),
        causation_id=str(causation_id) if causation_id else None,
        payload={"role": role},
    )
    conn.execute(
        """insert into public.events
           (id,workspace_id,session_id,event_type,producer_type,event_time,recorded_at,causation_id,correlation_id,schema_version,payload)
           values (%(id)s,%(workspace_id)s,%(session_id)s,%(event_type)s,%(producer_type)s,%(event_time)s,%(recorded_at)s,%(causation_id)s,%(correlation_id)s,%(schema_version)s,%(payload)s::jsonb)""",
        {**event, "payload": __import__("json").dumps(event["payload"])},
    )
    sequence = conn.execute(
        "select coalesce(max(sequence_no), -1) + 1 from public.messages where session_id = %s",
        (session_id,),
    ).fetchone()[0]
    message_id = uuid.uuid4()
    conn.execute(
        """insert into public.messages
           (id,workspace_id,session_id,event_id,role,content,source_id,sequence_no)
           values (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (message_id, workspace_id, session_id, event["id"], role, content, source_id, sequence),
    )
    return message_id, uuid.UUID(event["id"])
