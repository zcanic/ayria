/**
 * Shared event names and TypeScript-side event shapes.
 *
 * Keep names aligned with Python domain events. This package exists to prevent
 * desktop and runtime from drifting into incompatible vocabulary.
 */

export type RuntimeEventType =
  | 'window.changed'
  | 'clipboard.changed'
  | 'screenshot.captured'
  | 'user.message.received'
  | 'config.updated'
  | 'events.dropped'
  | 'task.updated'
  | 'assistant.message.created'
  | 'presence.updated'
  | 'world_state.patched'
  | 'tool.called'
  | 'tool.result'
  | 'tool.failed';
