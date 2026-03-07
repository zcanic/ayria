"""Task inspection endpoints.

Expose enough task state for the desktop app to render progress and for humans
or weaker agents to debug the runtime.
"""

from fastapi import APIRouter
from fastapi import HTTPException
import asyncio
from pydantic import BaseModel

from app.runtime_container import container

router = APIRouter(prefix='/tasks', tags=['tasks'])


class TaskDecisionRequest(BaseModel):
    approve: bool = True


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


@router.post('/{task_id}/decision')
def decide_task(task_id: str, request: TaskDecisionRequest) -> dict:
    task = container.task_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail='task not found')
    if task.status != 'awaiting_user':
        raise HTTPException(status_code=400, detail='task_not_awaiting_user')
    if task.type != 'tool_call':
        raise HTTPException(status_code=400, detail='task_decision_not_supported')

    tool_name = str(task.input_payload.get('tool_name', '')).strip()
    input_payload = dict(task.input_payload.get('input_payload') or {})
    tool = container.tool_service.get_tool(tool_name)
    if tool is None:
        raise HTTPException(status_code=400, detail=f'tool_not_found:{tool_name}')

    if not request.approve:
        updated = container.task_service.update_task(
            task.id,
            status='cancelled',
            output_payload={'decision': 'rejected', 'tool_name': tool_name},
        ) or task
        container.audit_repo.append(
            category='tool',
            action=tool_name,
            decision='rejected',
            summary=f'User rejected {tool_name}',
            metadata={'task_id': task.id},
        )
        container.event_stream.publish('task.updated', updated.model_dump())
        return {'status': 'rejected', 'task': updated.model_dump()}

    busy_state = container.presence_service.presence_for_tool_activity(tool_name=tool_name)
    busy_world_state = container.world_state_repo.set_presence(busy_state)
    container.event_stream.publish('presence.updated', busy_state.model_dump())
    container.event_stream.publish('world_state.patched', busy_world_state.model_dump())
    container.event_stream.publish(
        'tool.called',
        {
            'tool_name': tool_name,
            'confirmed': True,
            'permission_level': getattr(tool, 'permission_level', None),
            'data_sensitivity': getattr(tool, 'data_sensitivity', None),
            'approved_via_task': task.id,
        },
    )

    try:
        result = asyncio.run(
            container.tool_service.execute(
                tool_name=tool_name,
                input_payload=input_payload,
                confirmed=True,
            )
        )
    except Exception as error:
        updated = container.task_service.update_task(
            task.id,
            status='failed',
            output_payload={'decision': 'approved_but_failed', 'error': str(error), 'tool_name': tool_name},
        ) or task
        container.audit_repo.append(
            category='tool',
            action=tool_name,
            decision='failed',
            summary=str(error),
            metadata={'task_id': task.id},
        )
        container.event_stream.publish('tool.failed', {'tool_name': tool_name, 'error': str(error), 'approved_via_task': task.id})
        container.event_stream.publish('task.updated', updated.model_dump())
        raise HTTPException(status_code=400, detail=str(error))

    updated = container.task_service.update_task(
        task.id,
        status='completed',
        output_payload={
            'decision': 'approved',
            'tool_name': tool_name,
            'result': container.tool_service.summarize_result_for_event(tool_name=tool_name, result=result),
        },
    ) or task
    container.audit_repo.append(
        category='tool',
        action=tool_name,
        decision='approved',
        summary=f'User approved {tool_name}',
        metadata={'task_id': task.id, **container.tool_service.summarize_result_for_event(tool_name=tool_name, result=result)},
    )
    container.event_stream.publish('tool.result', {**container.tool_service.summarize_result_for_event(tool_name=tool_name, result=result), 'approved_via_task': task.id})
    container.event_stream.publish('task.updated', updated.model_dump())
    idle_world_state = container.world_state_repo.set_presence(
        container.presence_service.build_presence_state(mode='idle', user_active=True, reason='tool_execution_complete')
    )
    container.event_stream.publish('presence.updated', idle_world_state.presence.model_dump() if idle_world_state.presence else {})
    container.event_stream.publish('world_state.patched', idle_world_state.model_dump())
    return {'status': 'completed', 'task': updated.model_dump(), 'result': result}
