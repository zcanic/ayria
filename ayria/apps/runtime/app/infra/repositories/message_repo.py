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
