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


def _message(role: Any, content: Any, source_name: str, external_id: Any = None) -> ImportedMessage | None:
    normalized_role = str(role or "user").lower()
    if normalized_role in {"human", "user"}:
        normalized_role = "user"
    elif normalized_role in {"assistant", "model"}:
        normalized_role = "assistant"
    elif normalized_role not in {"system", "user", "assistant", "tool"}:
        normalized_role = "assistant"
    if isinstance(content, list):
        content = "\n".join(
            str(x.get("text", x.get("content", x))) if isinstance(x, dict) else str(x)
            for x in content
        )
    if isinstance(content, dict):
        content = content.get("text", content.get("content", ""))
    text = str(content or "").strip()
    if not text:
        return None
    return ImportedMessage(normalized_role, text, source_name, external_id=str(external_id) if external_id is not None else None)


def import_generic_conversation(payload: list[dict[str, Any]], source_name: str) -> list[ImportedMessage]:
    """Normalize a simple role/content conversation without treating model text as truth."""
    result: list[ImportedMessage] = []
    for index, item in enumerate(payload):
        parsed = _message(item.get("role", "user"), item.get("content", ""), source_name, item.get("id", index))
        if parsed:
            result.append(parsed)
    return result


def import_chatgpt_export(payload: dict[str, Any] | list[dict[str, Any]], source_name: str = "ChatGPT export") -> list[ImportedMessage]:
    """Normalize OpenAI ChatGPT conversations.json tree exports."""
    conversations = payload if isinstance(payload, list) else payload.get("conversations", [])
    result: list[ImportedMessage] = []
    for conversation in conversations:
        mapping = conversation.get("mapping", {})
        nodes = sorted(
            mapping.values(),
            key=lambda node: (node.get("message", {}).get("create_time") or 0),
        )
        for node in nodes:
            message = node.get("message") or {}
            author = message.get("author", {})
            content = message.get("content", {})
            parsed = _message(author.get("role"), content.get("parts", content), source_name, message.get("id"))
            if parsed:
                result.append(parsed)
    return result


def import_claude_export(payload: dict[str, Any] | list[dict[str, Any]], source_name: str = "Claude export") -> list[ImportedMessage]:
    """Normalize common Anthropic/Claude export conversation structures."""
    conversations = payload if isinstance(payload, list) else payload.get("conversations", [payload])
    result: list[ImportedMessage] = []
    for conversation in conversations:
        messages = conversation.get("chat_messages", conversation.get("messages", []))
        for item in messages:
            parsed = _message(
                item.get("sender", item.get("role")),
                item.get("text", item.get("content", "")),
                source_name,
                item.get("uuid", item.get("id")),
            )
            if parsed:
                result.append(parsed)
    return result


def import_gemini_export(payload: dict[str, Any] | list[dict[str, Any]], source_name: str = "Gemini export") -> list[ImportedMessage]:
    """Normalize common Google Gemini Takeout conversation structures."""
    conversations = payload if isinstance(payload, list) else payload.get("conversations", [payload])
    result: list[ImportedMessage] = []
    for conversation in conversations:
        messages = conversation.get("messages", conversation.get("turns", []))
        for index, item in enumerate(messages):
            parsed = _message(
                item.get("role", item.get("author")),
                item.get("content", item.get("text", "")),
                source_name,
                item.get("id", index),
            )
            if parsed:
                result.append(parsed)
    return result
