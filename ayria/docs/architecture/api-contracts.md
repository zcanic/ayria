# API Contracts

## Philosophy

Routes should be boring.
They should convert transport-level data into domain service calls and return a stable response shape.
They should not own orchestration logic.

## Base Paths

- HTTP: `/api/v1`
- WebSocket: `/api/v1/ws`

## Health

### `GET /api/v1/health`

Purpose:
- runtime liveness check
- desktop startup check
- CI smoke test

### `GET /api/v1/health/providers`

Purpose:
- provider inventory
- local model connectivity status
- cloud fallback availability

## Chat

### `POST /api/v1/chat/send`

This route should:
- create a task
- enqueue or execute the task
- return an acceptance response quickly

It should not:
- hold the HTTP request open for the full assistant pipeline unless a streaming mode is explicitly added later

Recommended response shape:

```json
{
  "status": "accepted",
  "taskId": "task_123",
  "requestId": "req_123"
}
```

## Events

### `POST /api/v1/events/window-changed`

Use when active app or title changes significantly.
The runtime may decide to ignore no-op changes.

### `POST /api/v1/events/screenshot-captured`

Use only when a screenshot was actually captured by policy.
Do not call this route just to ask the runtime whether a screenshot should be taken.

## World State

### `GET /api/v1/world-state`

This is a debug and observability route.
It should be safe for local use and power the debug UI.

## Tasks

### `GET /api/v1/tasks`

For debug UI and operational visibility.
Do not expose every internal field by default if it becomes noisy.

## Config

### `GET /api/v1/config`
### `PUT /api/v1/config`

Config changes should produce a `config.updated` event so the desktop can react.

## Provider Inventory

### `GET /api/v1/providers`

Useful for settings UI and diagnostics.
Should eventually describe:
- provider name
- endpoint
- enabled state
- health
- supported features: text, vision, tools
