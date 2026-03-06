from typing import Literal

from app.domain.models.task import Task
from app.infra.repositories.task_repo import TaskRepository, TaskType

TaskStatus = Literal['queued', 'running', 'awaiting_user', 'completed', 'failed', 'cancelled']

class TaskService:
    def __init__(self, repo: TaskRepository) -> None:
        self._repo = repo

    def create_task(self, task_type: TaskType, payload: dict, trigger_event_id: str | None = None, priority: int = 5) -> Task:
        return self._repo.create(task_type=task_type, payload=payload, trigger_event_id=trigger_event_id, priority=priority)

    def update_task(self, task_id: str, status: TaskStatus, output_payload: dict | None = None) -> Task | None:
        return self._repo.update_status(task_id=task_id, status=status, output_payload=output_payload)

    def get_task(self, task_id: str) -> Task | None:
        return self._repo.get(task_id)

    def list_tasks(self) -> list[Task]:
        return self._repo.list()
