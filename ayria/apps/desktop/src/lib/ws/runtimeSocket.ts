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

export function connectRuntimeSocket() {
  return {
    enabled: false,
    reason: 'event_streaming_not_enabled_in_v1',
  } as const;
}
