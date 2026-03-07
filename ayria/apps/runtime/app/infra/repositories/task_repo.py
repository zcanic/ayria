from datetime import datetime, timezone
from threading import Lock
from typing import Literal

from app.domain.models.task import Task

TaskType = Literal[
    'chat_reply',
    'proactive_observation',
    'screenshot_analysis',
    'web_search',
    'memory_extract',
    'tool_call',
    'reflection',
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskRepository:
    def __init__(self) -> None:
        self._items: dict[str, Task] = {}
        self._seq = 0
        self._lock = Lock()

    def create(self, task_type: TaskType, payload: dict, trigger_event_id: str | None = None, priority: int = 5) -> Task:
        with self._lock:
            self._seq += 1
            task_id = f"task_{self._seq:06d}"
            now = _now_iso()
            task = Task(
                id=task_id,
                type=task_type,
                status='queued',
                priority=priority,
                trigger_event_id=trigger_event_id,
                input_payload=payload,
                output_payload=None,
                created_at=now,
                updated_at=now,
            )
            self._items[task_id] = task
            return task.model_copy(deep=True)

    def update_status(self, task_id: str, status: str, output_payload: dict | None = None) -> Task | None:
        with self._lock:
            current = self._items.get(task_id)
            if current is None:
                return None
            next_payload = output_payload if output_payload is not None else current.output_payload
            updated = current.model_copy(
                update={
                    'status': status,
                    'output_payload': next_payload,
                    'updated_at': _now_iso(),
                }
            )
            self._items[task_id] = updated
            return updated.model_copy(deep=True)

    def get(self, task_id: str) -> Task | None:
        with self._lock:
            item = self._items.get(task_id)
            return item.model_copy(deep=True) if item else None

    def list(self) -> list[Task]:
        with self._lock:
            return [item.model_copy(deep=True) for item in sorted(self._items.values(), key=lambda value: value.created_at, reverse=True)]
