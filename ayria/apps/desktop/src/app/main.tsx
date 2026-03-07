import { App } from './App';
import { getHealth, getWorldState, sendChat } from '../lib/api/client';
import { connectRuntimeSocket, type RuntimeEvent } from '../lib/ws/runtimeSocket';

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

  let latestState = await getWorldState();
  const transport = connectRuntimeSocket((event) => {
    handleRuntimeEvent(event);
  });
  const health = await getHealth();

  const presenceNode = document.getElementById('presence-status');
  if (presenceNode) {
    presenceNode.textContent = `Mode: ${latestState.presence?.mode ?? 'idle'}`;
  }
  const runtimeHealthNode = document.getElementById('runtime-health');
  if (runtimeHealthNode) {
    runtimeHealthNode.textContent = `Runtime: ${health.status}`;
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
    worldStateNode.textContent = JSON.stringify(latestState, null, 2);
  }

  const proactiveNode = document.getElementById('settings-proactive');
  if (proactiveNode) {
    proactiveNode.textContent = `Proactive: ${latestState.presence?.proactive_allowed ? 'enabled' : 'disabled'}`;
  }

  const providerNode = document.getElementById('settings-provider');
  if (providerNode) {
    providerNode.textContent = 'Provider: local-first (ollama)';
  }

  const sendButton = document.getElementById('chat-send-button');
  const input = document.getElementById('chat-input') as HTMLTextAreaElement | null;
  const messages = document.getElementById('chat-messages');
  if (sendButton && input && messages) {
    sendButton.addEventListener('click', async () => {
      const text = input.value.trim();
      if (!text) {
        return;
      }
      appendMessage(messages, 'user', text);
      input.value = '';
      const response = await sendChat(text);
      if (response.error) {
        appendMessage(messages, 'system', `Error: ${response.error}`);
      }
      latestState = await getWorldState();
      const nextWorldStateNode = document.getElementById('world-state');
      if (nextWorldStateNode) {
        nextWorldStateNode.textContent = JSON.stringify(latestState, null, 2);
      }
    });
  }
}

void bootstrapDesktopApp();

function handleRuntimeEvent(event: RuntimeEvent) {
  if (event.type === 'presence.updated') {
    const presenceNode = document.getElementById('presence-status');
    if (presenceNode) {
      presenceNode.textContent = `Mode: ${String(event.payload.mode ?? 'idle')}`;
    }
  }

  if (event.type === 'world_state.patched') {
    const worldStateNode = document.getElementById('world-state');
    if (worldStateNode) {
      worldStateNode.textContent = JSON.stringify(event.payload, null, 2);
    }
  }

  if (event.type === 'assistant.message.created') {
    const messages = document.getElementById('chat-messages');
    const parts = Array.isArray((event.payload as { parts?: unknown[] }).parts)
      ? ((event.payload as { parts?: Array<{ type?: string; text?: string | null }> }).parts ?? [])
      : [];
    const text = parts.find((part) => part.type === 'text')?.text;
    if (messages && text) {
      appendMessage(messages, 'assistant', text);
    }
  }
}

function appendMessage(container: HTMLElement, role: 'user' | 'assistant' | 'system', text: string) {
  if (container.textContent === 'No messages yet.') {
    container.textContent = '';
  }
  const line = document.createElement('div');
  line.setAttribute('data-role', role);
  line.textContent = `${role}: ${text}`;
  container.appendChild(line);
}
