"""Task inspection endpoints.

Expose enough task state for the desktop app to render progress and for humans
or weaker agents to debug the runtime.
"""

from fastapi import APIRouter
from fastapi import HTTPException

from app.runtime_container import container

router = APIRouter(prefix='/tasks', tags=['tasks'])


@router.get('')
def list_tasks() -> dict:
    items = [task.model_dump() for task in container.task_service.list_tasks()]
    return {'items': items}


@router.get('/{task_id}')
def get_task(task_id: str) -> dict:
    task = container.task_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail='task not found')
    return task.model_dump()
