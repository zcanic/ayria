"""Simple in-process event stream for runtime-to-desktop updates.

This is not a full event bus, but it is a truthful real transport:
- routes and services can publish structured events
- websocket clients can subscribe and receive ordered updates

The implementation intentionally favors reliability and debuggability over
clever concurrency.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import Lock


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventStream:
    def __init__(self, max_events: int = 256) -> None:
        self._events: deque[dict] = deque(maxlen=max_events)
        self._next_seq = 1
        self._lock = Lock()
        self._max_events = max_events

    def publish(self, event_type: str, payload: dict, *, source: str = 'runtime') -> dict:
        with self._lock:
            seq = self._next_seq
            event = {
                'id': f'evt_{seq:09d}',
                'seq': seq,
                'type': event_type,
                'source': source,
                'timestamp': _now_iso(),
                'payload': payload,
            }
            self._next_seq += 1
            self._events.append(event)
            return dict(event)

    def list_after(self, seq: int) -> list[dict]:
        with self._lock:
            return [dict(event) for event in self._events if int(event['seq']) > seq]

    def oldest_seq(self) -> int | None:
        with self._lock:
            if not self._events:
                return None
            return int(self._events[0]['seq'])

    def make_transient_event(self, event_type: str, payload: dict, *, source: str = 'runtime', seq: int = 0) -> dict:
        return {
            'id': f'transient_{event_type}_{seq}',
            'seq': seq,
            'type': event_type,
            'source': source,
            'timestamp': _now_iso(),
            'payload': payload,
        }
