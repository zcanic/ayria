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

    container.event_stream.publish(
        'tool.result',
        container.tool_service.summarize_result_for_event(tool_name=request.tool_name, result=result),
    )
    return {'tool_name': request.tool_name, 'result': result}
