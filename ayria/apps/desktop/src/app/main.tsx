import { App } from './App';
import { getHealth, getWorldState } from '../lib/api/client';
import { connectRuntimeSocket } from '../lib/ws/runtimeSocket';

/**
 * Desktop entry placeholder.
 *
 * This file is intentionally small.
 * A weaker agent should be able to replace this with a real React bootstrap
 * without having to understand the full product architecture first.
 *
 * Immediate next step:
 * - render the app shell
 * - connect a state store
 * - initialize HTTP and WebSocket clients
 */

export async function bootstrapDesktopApp() {
  const root = document.getElementById('app');
  if (!root) {
    return;
  }

  root.innerHTML = App();

  const transport = connectRuntimeSocket();

  const health = await getHealth();
  const state = await getWorldState();

  const presenceNode = document.getElementById('presence-status');
  if (presenceNode) {
    presenceNode.textContent = `Mode: ${state.presence?.mode ?? 'idle'} | Runtime: ${health.status}`;
  }

  const transportNode = document.getElementById('transport-status');
  if (transportNode) {
    if (transport.enabled) {
      transportNode.textContent = 'Events: websocket enabled';
    } else {
      transportNode.textContent = `Events: disabled (${transport.reason})`;
    }
  }

  const worldStateNode = document.getElementById('world-state');
  if (worldStateNode) {
    worldStateNode.textContent = JSON.stringify(state, null, 2);
  }
}

void bootstrapDesktopApp();
