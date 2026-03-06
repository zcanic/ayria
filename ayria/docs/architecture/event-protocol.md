# Event Protocol

## Why Events Matter

ayria should be event-driven so the system can respond to both user messages and environmental signals in a consistent way.

## Event Envelope

All internal and transport-level events should fit this shape:

```json
{
  "id": "evt_123",
  "type": "window.changed",
  "source": "desktop",
  "timestamp": "2026-03-07T09:00:00Z",
  "payload": {}
}
```

## Event Naming Rules

Use dotted names and keep them short.

Good:
- `window.changed`
- `screenshot.captured`
- `assistant.message.created`

Bad:
- `windowChangedEvent`
- `assistantResponded`

## Core Event Families

### Environment
- `window.changed`
- `clipboard.changed`
- `screenshot.captured`
- `user.idle`
- `user.returned`

### User
- `user.message.received`
- `user.command.received`

### Runtime
- `task.created`
- `task.updated`
- `presence.updated`
- `world_state.patched`

### Assistant
- `assistant.message.created`
- `assistant.typing`
- `assistant.proactive.suggested`

### Tooling
- `tool.called`
- `tool.result`
- `tool.failed`

## Delivery Rules

### HTTP Ingress

Desktop shell or watcher submits events via HTTP when simplicity matters.
This is best for v1.

### WebSocket Egress

Runtime publishes state and assistant events to the desktop over WebSocket.
This lets the UI update without polling.

## Ordering Expectations

Do not assume total event ordering across the whole system.
Do assume per-request or per-task local order when possible.

## Idempotency Guidance

Environment watchers may produce duplicate signals.
The runtime should tolerate repeated `window.changed` and `screenshot.captured` events.
