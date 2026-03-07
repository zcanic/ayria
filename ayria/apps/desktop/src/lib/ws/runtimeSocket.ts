/**
 * Runtime WebSocket placeholder.
 *
 * The desktop UI should subscribe to runtime events rather than poll for
 * everything. This file is the single place to manage that socket.
 *
 * Planned event families:
 * - presence.updated
 * - world_state.patched
 * - assistant.message.created
 * - task.updated
 * - tool.called
 * - tool.result
 */

export type RuntimeEvent =
  | { type: 'connection.ready'; payload: { status: string } }
  | { type: 'presence.updated'; payload: Record<string, unknown> }
  | { type: 'world_state.patched'; payload: Record<string, unknown> }
  | { type: 'assistant.message.created'; payload: Record<string, unknown> }
  | { type: 'task.updated'; payload: Record<string, unknown> }
  | { type: 'tool.result'; payload: Record<string, unknown> };

export function connectRuntimeSocket(onEvent: (event: RuntimeEvent) => void) {
  const url = 'ws://127.0.0.1:8000/api/v1/ws';
  const socket = new WebSocket(url);

  socket.onmessage = (message) => {
    try {
      onEvent(JSON.parse(message.data) as RuntimeEvent);
    } catch {
      // Ignore malformed messages so UI remains usable during development.
    }
  };

  return {
    enabled: true,
    reason: undefined as string | undefined,
    socket,
    close: () => socket.close(),
  } as const;
}
