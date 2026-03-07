from __future__ import annotations

from app.domain.models.message import ChatMessage, MessagePart
from app.domain.models.world_state import WorldState


class ProactiveService:
    def __init__(self, *, proactive_mode: str = 'balanced') -> None:
        self._proactive_mode = proactive_mode

    def suggest_for_world_state(self, world_state: WorldState) -> str | None:
        active_window = world_state.active_window
        if active_window is None:
            return None

        app = (active_window.app_name or '').lower()
        title = active_window.window_title or ''

        if 'cursor' in app or 'vscode' in app:
            return f'I can review `{title}` for bugs, summarize the current file, or suggest the next coding step.'
        if any(name in app for name in ('chrome', 'safari', 'firefox', 'arc', 'edge')):
            return f'I can summarize `{title}`, extract action items, or research related links when you want.'
        if any(name in app for name in ('notion', 'pages', 'word', 'preview')):
            return f'I can turn `{title}` into notes, action items, or a concise summary.'
        if self._proactive_mode == 'active':
            return f'I am tracking `{title}` and can help if you want a summary, search, or next-step suggestion.'
        return None

    def build_message(self, *, message_id: str, text: str, created_at: str) -> ChatMessage:
        return ChatMessage(
            id=message_id,
            role='assistant',
            source='proactive',
            parts=[MessagePart(type='text', text=text)],
            created_at=created_at,
        )
