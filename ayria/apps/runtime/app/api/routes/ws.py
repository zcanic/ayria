"""Runtime WebSocket event stream."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.runtime_container import container

router = APIRouter(tags=['ws'])


@router.websocket('/ws')
async def runtime_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json(
        container.event_stream.make_transient_event(
            'connection.ready',
            {'status': 'connected'},
            source='runtime',
        )
    )
    cursor = 0
    try:
        while True:
            oldest_seq = container.event_stream.oldest_seq()
            if oldest_seq is not None and cursor and cursor < oldest_seq - 1:
                dropped_to = oldest_seq - 1
                await websocket.send_json(
                    container.event_stream.make_transient_event(
                        'events.dropped',
                        {
                            'from_seq': cursor + 1,
                            'to_seq': dropped_to,
                            'dropped_count': dropped_to - cursor,
                        },
                        source='runtime',
                        seq=cursor,
                    )
                )
                cursor = dropped_to
            events = container.event_stream.list_after(cursor)
            for event in events:
                cursor = int(event['seq'])
                await websocket.send_json(event)
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        return
