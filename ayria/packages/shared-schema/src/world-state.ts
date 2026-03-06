/**
 * Shared world state summary types.
 *
 * Only put fields here that the desktop app genuinely needs. Full runtime state
 * can remain richer on the Python side.
 */

export type PresenceMode = 'idle' | 'observing' | 'chatting' | 'busy' | 'sleeping';

export type WorldStateSummary = {
  activeWindowTitle?: string;
  activeAppName?: string;
  presenceMode?: PresenceMode;
  currentTaskHint?: string;
};
