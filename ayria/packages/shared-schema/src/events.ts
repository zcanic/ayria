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
  | 'task.updated'
  | 'assistant.message.created'
  | 'presence.updated'
  | 'world_state.patched';
