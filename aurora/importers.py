from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ImportedMessage:
    role: str
    content: str
    source_name: str
    created_at: datetime | None = None
    external_id: str | None = None


def import_generic_conversation(payload: list[dict[str, Any]], source_name: str) -> list[ImportedMessage]:
    """Normalize a simple role/content conversation without treating model text as truth."""
    result: list[ImportedMessage] = []
    for index, item in enumerate(payload):
        role = str(item.get("role", "user"))
        if role not in {"system", "user", "assistant", "tool"}:
            role = "assistant"
        content = item.get("content", "")
        if isinstance(content, list):
            content = "\n".join(str(x.get("text", x)) if isinstance(x, dict) else str(x) for x in content)
        if not str(content).strip():
            continue
        result.append(
            ImportedMessage(
                role=role,
                content=str(content),
                source_name=source_name,
                external_id=str(item.get("id", index)),
            )
        )
    return result
