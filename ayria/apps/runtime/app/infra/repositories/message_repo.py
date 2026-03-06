from app.domain.models.message import ChatMessage


class MessageRepository:
    def __init__(self) -> None:
        self._items: list[ChatMessage] = []

    def append(self, message: ChatMessage) -> ChatMessage:
        self._items.append(message)
        return message.model_copy(deep=True)

    def list_recent(self, limit: int = 20) -> list[ChatMessage]:
        items = self._items[-limit:]
        return [item.model_copy(deep=True) for item in items]

    def list_recent_for_context(self, limit: int = 12) -> list[str]:
        recent = self.list_recent(limit=limit)
        lines: list[str] = []
        for message in recent:
            text_parts = [part.text for part in message.parts if part.type == 'text' and part.text]
            if not text_parts:
                continue
            lines.append(f"{message.role.upper()}: {' '.join(text_parts)}")
        return lines
