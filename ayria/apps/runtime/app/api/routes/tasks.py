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


def _format_error_reason(error: Exception) -> str:
    text = str(error).strip()
    if text:
        return text
    return f'{type(error).__name__}:{repr(error)}'


class TaskDecisionRequest(BaseModel):
    approve: bool = True


@router.get('')
def list_tasks() -> dict[str, list[dict[str, object]]]:
    items = [task.model_dump() for task in container.task_service.list_tasks()]
    return {'items': items}


@router.get('/{task_id}')
def get_task(task_id: str) -> dict[str, object]:
    task = container.task_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail='task not found')
    return task.model_dump()


@router.post('/{task_id}/decision')
def decide_task(task_id: str, request: TaskDecisionRequest) -> dict[str, object]:
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

    parent_chat_task_id = str(task.input_payload.get('parent_chat_task_id', '')).strip()
    continuation = task.input_payload.get('continuation') if isinstance(task.input_payload.get('continuation'), dict) else None

    if not request.approve:
        updated = container.task_service.transition_task(
            task.id,
            expected_status='awaiting_user',
            next_status='cancelled',
            output_payload={'decision': 'rejected', 'tool_name': tool_name, 'response_mode': 'ask_permission'},
        )
        if updated is None:
            raise HTTPException(status_code=409, detail='task_not_awaiting_user')

        if parent_chat_task_id:
            parent_task = container.task_service.get_task(parent_chat_task_id)
            if parent_task is not None and parent_task.status == 'awaiting_user':
                parent_updated = container.task_service.update_task(
                    parent_task.id,
                    status='cancelled',
                    output_payload={
                        **(parent_task.output_payload or {}),
                        'response_mode': 'respond_now',
                        'reason': f'tool_rejected:{tool_name}',
                    },
                )
                if parent_updated is not None:
                    container.event_stream.publish('task.updated', parent_updated.model_dump())

        container.audit_repo.append(
            category='tool',
            action=tool_name,
            decision='rejected',
            summary=f'User rejected {tool_name}',
            metadata={'task_id': task.id},
        )
        container.event_stream.publish('task.updated', updated.model_dump())
        return {'status': 'rejected', 'task': updated.model_dump()}

    running_task = container.task_service.transition_task(
        task.id,
        expected_status='awaiting_user',
        next_status='running',
        output_payload={
            'decision': 'approved_pending_execution',
            'tool_name': tool_name,
            'response_mode': 'respond_now',
        },
    )
    if running_task is None:
        raise HTTPException(status_code=409, detail='task_not_awaiting_user')
    container.event_stream.publish('task.updated', running_task.model_dump())

    current_permission = container.permission_policy_service.evaluate(tool=tool, confirmed=True)
    if current_permission.decision == 'denied':
        updated = container.task_service.update_task(
            running_task.id,
            status='cancelled',
            output_payload={
                'decision': 'denied_by_current_policy',
                'tool_name': tool_name,
                'reason': current_permission.reason,
                'response_mode': 'ask_permission',
            },
        ) or running_task
        container.audit_repo.append(
            category='tool',
            action=tool_name,
            decision='denied',
            summary=f'Current policy denied {tool_name} after approval',
            metadata={'task_id': running_task.id, 'reason': current_permission.reason},
        )
        if parent_chat_task_id:
            parent_task = container.task_service.get_task(parent_chat_task_id)
            if parent_task is not None and parent_task.status in {'awaiting_user', 'running'}:
                parent_updated = container.task_service.update_task(
                    parent_task.id,
                    status='failed',
                    output_payload={
                        **(parent_task.output_payload or {}),
                        'inference_mode': 'provider_error',
                        'provider_call_occurred': True,
                        'reason': current_permission.reason,
                    },
                )
                if parent_updated is not None:
                    container.event_stream.publish('task.updated', parent_updated.model_dump())
        container.event_stream.publish('task.updated', updated.model_dump())
        return {'status': 'denied_by_policy', 'reason': current_permission.reason, 'response_mode': 'ask_permission', 'task': updated.model_dump()}

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
            'approved_via_task': running_task.id,
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
            running_task.id,
            status='failed',
            output_payload={'decision': 'approved_but_failed', 'error': str(error), 'tool_name': tool_name},
        ) or running_task
        if parent_chat_task_id:
            parent_task = container.task_service.get_task(parent_chat_task_id)
            if parent_task is not None and parent_task.status in {'awaiting_user', 'running'}:
                parent_updated = container.task_service.update_task(
                    parent_task.id,
                    status='failed',
                    output_payload={
                        **(parent_task.output_payload or {}),
                        'inference_mode': 'provider_error',
                        'provider_call_occurred': True,
                        'reason': f'tool_execution_failed:{tool_name}:{_format_error_reason(error)}',
                    },
                )
                if parent_updated is not None:
                    container.event_stream.publish('task.updated', parent_updated.model_dump())
        container.audit_repo.append(
            category='tool',
            action=tool_name,
            decision='failed',
            summary=str(error),
            metadata={'task_id': running_task.id},
        )
        container.event_stream.publish('tool.failed', {'tool_name': tool_name, 'error': str(error), 'approved_via_task': running_task.id})
        container.event_stream.publish('task.updated', updated.model_dump())
        raise HTTPException(status_code=400, detail=str(error))

    updated = container.task_service.update_task(
        running_task.id,
        status='completed',
        output_payload={
            'decision': 'approved',
            'tool_name': tool_name,
            'response_mode': 'respond_now',
            'result': container.tool_service.summarize_result_for_event(tool_name=tool_name, result=result),
        },
    ) or running_task
    container.audit_repo.append(
        category='tool',
        action=tool_name,
        decision='approved',
        summary=f'User approved {tool_name}',
        metadata={'task_id': running_task.id, **container.tool_service.summarize_result_for_event(tool_name=tool_name, result=result)},
    )
    container.event_stream.publish('tool.result', {**container.tool_service.summarize_result_for_event(tool_name=tool_name, result=result), 'approved_via_task': running_task.id})
    container.event_stream.publish('task.updated', updated.model_dump())
    idle_world_state = container.world_state_repo.set_presence(
        container.presence_service.build_presence_state(mode='idle', user_active=True, reason='tool_execution_complete')
    )
    container.event_stream.publish('presence.updated', idle_world_state.presence.model_dump() if idle_world_state.presence else {})
    container.event_stream.publish('world_state.patched', idle_world_state.model_dump())

    if continuation is not None:
        if not parent_chat_task_id:
            raise HTTPException(status_code=400, detail='chat_continuation_missing_parent_task')
        parent_task = container.task_service.get_task(parent_chat_task_id)
        if parent_task is None:
            raise HTTPException(status_code=404, detail=f'chat_continuation_parent_task_not_found:{parent_chat_task_id}')
        if parent_task.status not in {'awaiting_user', 'running'}:
            raise HTTPException(status_code=409, detail=f'chat_continuation_parent_task_invalid_status:{parent_task.status}')

        if parent_task.status == 'awaiting_user':
            parent_running = container.task_service.transition_task(
                parent_task.id,
                expected_status='awaiting_user',
                next_status='running',
                output_payload={
                    **(parent_task.output_payload or {}),
                    'response_mode': 'respond_now',
                    'continued_by_tool_task_id': running_task.id,
                },
            )
            if parent_running is None:
                raise HTTPException(status_code=409, detail='chat_continuation_parent_task_not_awaiting_user')
            container.event_stream.publish('task.updated', parent_running.model_dump())

        chat_response = container.orchestrator.continue_chat_after_tool(
            continuation=continuation,
            tool_name=tool_name,
            tool_result=result,
        )
        return {
            'status': 'completed',
            'response_mode': 'respond_now',
            'task': updated.model_dump(),
            'result': result,
            'chat_response': chat_response,
        }

    return {'status': 'completed', 'response_mode': 'respond_now', 'task': updated.model_dump(), 'result': result}
