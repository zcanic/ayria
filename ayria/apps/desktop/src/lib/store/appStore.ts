/**
 * App state placeholder.
 *
 * Keep local UI state here.
 * Do not store durable memory or business rules in the UI store.
 * Those belong in the runtime.
 */

export type PresenceMode = 'idle' | 'observing' | 'chatting' | 'busy' | 'sleeping';

export type AppStoreState = {
  presenceMode: PresenceMode;
  runtimeConnected: boolean;
};
