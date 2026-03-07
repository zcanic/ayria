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
    container.event_stream.publish(
        'tool.called',
        {
            'tool_name': request.tool_name,
            'confirmed': request.confirmed,
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
        raise HTTPException(status_code=400, detail=str(error))

    container.event_stream.publish(
        'tool.result',
        {
            'tool_name': request.tool_name,
            'result': result,
        },
    )
    return {'tool_name': request.tool_name, 'result': result}
