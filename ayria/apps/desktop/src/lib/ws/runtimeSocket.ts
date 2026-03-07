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
  | { id: string; seq: number; source: string; timestamp: string; type: 'connection.ready'; payload: { status: string } }
  | { id: string; seq: number; source: string; timestamp: string; type: 'events.dropped'; payload: Record<string, unknown> }
  | { id: string; seq: number; source: string; timestamp: string; type: 'config.updated'; payload: Record<string, unknown> }
  | { id: string; seq: number; source: string; timestamp: string; type: 'permission.requested'; payload: Record<string, unknown> }
  | { id: string; seq: number; source: string; timestamp: string; type: 'assistant.proactive.suggested'; payload: Record<string, unknown> }
  | { id: string; seq: number; source: string; timestamp: string; type: 'presence.updated'; payload: Record<string, unknown> }
  | { id: string; seq: number; source: string; timestamp: string; type: 'world_state.patched'; payload: Record<string, unknown> }
  | { id: string; seq: number; source: string; timestamp: string; type: 'assistant.message.created'; payload: Record<string, unknown> }
  | { id: string; seq: number; source: string; timestamp: string; type: 'task.updated'; payload: Record<string, unknown> }
  | { id: string; seq: number; source: string; timestamp: string; type: 'tool.called'; payload: Record<string, unknown> }
  | { id: string; seq: number; source: string; timestamp: string; type: 'tool.result'; payload: Record<string, unknown> }
  | { id: string; seq: number; source: string; timestamp: string; type: 'tool.failed'; payload: Record<string, unknown> };

export function connectRuntimeSocket(onEvent: (event: RuntimeEvent) => void) {
  const url = 'ws://127.0.0.1:8000/api/v1/ws';
  const socket = new WebSocket(url);

  socket.onmessage = (message) => {
    try {
      onEvent(JSON.parse(message.data) as RuntimeEvent);
    } catch (error) {
      console.warn('runtime_socket_message_parse_failed', error);
    }
  };

  return {
    enabled: true,
    reason: undefined as string | undefined,
    socket,
    close: () => socket.close(),
  } as const;
}
