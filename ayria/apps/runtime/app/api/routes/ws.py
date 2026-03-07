"""Runtime WebSocket event stream."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.runtime_container import container

router = APIRouter(tags=['ws'])


@router.websocket('/ws')
async def runtime_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json({'type': 'connection.ready', 'payload': {'status': 'connected'}})
    cursor = 0
    try:
        while True:
            events = container.event_stream.list_after(cursor)
            for event in events:
                cursor = int(event['seq'])
                await websocket.send_json(event)
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        return
