"""Chat message models.

These models should become the stable language of the runtime.
Do not let route-specific payload shapes proliferate across the codebase.
"""

from pydantic import BaseModel
from typing import Literal


class MessagePart(BaseModel):
    type: Literal['text', 'image', 'tool_result']
    text: str | None = None
    image_url: str | None = None
    tool_name: str | None = None
    payload: dict | None = None


class ChatMessage(BaseModel):
    id: str
    role: Literal['user', 'assistant', 'system', 'tool']
    source: Literal['ui', 'proactive', 'tool', 'memory', 'system']
    parts: list[MessagePart]
    created_at: str
