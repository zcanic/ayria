"""Tool inventory and execution routes."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.runtime_container import container

router = APIRouter(prefix='/tools', tags=['tools'])


class ExecuteToolRequest(BaseModel):
    tool_name: str
    input_payload: dict = Field(default_factory=dict)
    confirmed: bool = False


@router.get('')
def list_tools() -> dict:
    return {'items': container.tool_service.list_tools()}


@router.post('/execute')
def execute_tool(request: ExecuteToolRequest) -> dict:
    tool = container.tool_service.get_tool(request.tool_name)
    if tool is None:
        raise HTTPException(status_code=404, detail=f'tool_not_found:{request.tool_name}')
    permission = container.permission_policy_service.evaluate(tool=tool, confirmed=request.confirmed)
    if permission.decision == 'denied':
        container.audit_repo.append(
            category='tool',
            action=request.tool_name,
            decision='denied',
            summary=permission.reason,
            metadata=container.permission_policy_service.describe_tool_policy(tool),
        )
        raise HTTPException(status_code=403, detail=permission.reason)
    if permission.requires_approval:
        approval_task = container.task_service.create_task(
            task_type='tool_call',
            payload={
                'tool_name': request.tool_name,
                'input_payload': request.input_payload,
                'permission': container.permission_policy_service.describe_tool_policy(tool),
            },
            priority=4,
        )
        approval_task = container.task_service.update_task(
            approval_task.id,
            status='awaiting_user',
            output_payload={'reason': permission.reason, 'tool_name': request.tool_name},
        ) or approval_task
        container.audit_repo.append(
            category='tool',
            action=request.tool_name,
            decision='approval_required',
            summary=permission.reason,
            metadata={'task_id': approval_task.id, **container.permission_policy_service.describe_tool_policy(tool)},
        )
        container.event_stream.publish(
            'permission.requested',
            {
                'task_id': approval_task.id,
                'tool_name': request.tool_name,
                'reason': permission.reason,
                **container.permission_policy_service.describe_tool_policy(tool),
            },
        )
        container.event_stream.publish('task.updated', approval_task.model_dump())
        return {
            'status': 'awaiting_approval',
            'task': approval_task.model_dump(),
            'tool_name': request.tool_name,
            'reason': permission.reason,
        }

    busy_state = container.presence_service.presence_for_tool_activity(tool_name=request.tool_name)
    busy_world_state = container.world_state_repo.set_presence(busy_state)
    container.event_stream.publish('presence.updated', busy_state.model_dump())
    container.event_stream.publish('world_state.patched', busy_world_state.model_dump())
    container.event_stream.publish(
        'tool.called',
        {
            'tool_name': request.tool_name,
            'confirmed': request.confirmed,
            'permission_level': getattr(tool, 'permission_level', None),
            'data_sensitivity': getattr(tool, 'data_sensitivity', None),
        },
    )
    try:
        result = asyncio.run(
            container.tool_service.execute(
                tool_name=request.tool_name,
                input_payload=request.input_payload,
                confirmed=request.confirmed,
            )
        )
    except Exception as error:
        container.audit_repo.append(
            category='tool',
            action=request.tool_name,
            decision='denied',
            summary=str(error),
            metadata={
                'confirmed': request.confirmed,
                'permission_level': getattr(tool, 'permission_level', None),
                'data_sensitivity': getattr(tool, 'data_sensitivity', None),
            },
        )
        container.event_stream.publish(
            'tool.failed',
            {
                'tool_name': request.tool_name,
                'permission_level': getattr(tool, 'permission_level', None),
                'data_sensitivity': getattr(tool, 'data_sensitivity', None),
                'error': str(error),
            },
        )
        raise HTTPException(status_code=400, detail=str(error))

    container.audit_repo.append(
        category='tool',
        action=request.tool_name,
        decision='allowed',
        summary=f'Executed {request.tool_name}',
        metadata=container.tool_service.summarize_result_for_event(tool_name=request.tool_name, result=result),
    )
    container.event_stream.publish(
        'tool.result',
        container.tool_service.summarize_result_for_event(tool_name=request.tool_name, result=result),
    )
    idle_world_state = container.world_state_repo.set_presence(
        container.presence_service.build_presence_state(mode='idle', user_active=True, reason='tool_execution_complete')
    )
    container.event_stream.publish('presence.updated', idle_world_state.presence.model_dump() if idle_world_state.presence else {})
    container.event_stream.publish('world_state.patched', idle_world_state.model_dump())
    return {'tool_name': request.tool_name, 'result': result}
