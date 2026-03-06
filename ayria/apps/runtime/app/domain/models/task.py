"""Task models.

All meaningful runtime work should become a task, even if that task is simple.
That gives the desktop app something observable to render and debug.
"""

from pydantic import BaseModel
from typing import Literal


class Task(BaseModel):
    id: str
    type: Literal[
        'chat_reply',
        'proactive_observation',
        'screenshot_analysis',
        'web_search',
        'memory_extract',
        'tool_call',
        'reflection',
    ]
    status: Literal['queued', 'running', 'awaiting_user', 'completed', 'failed', 'cancelled']
    priority: int
    trigger_event_id: str | None = None
    input_payload: dict
    output_payload: dict | None = None
    created_at: str
    updated_at: str
