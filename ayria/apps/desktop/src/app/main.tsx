import { App } from './App';
import {
  decideTask,
  getAuditLogs,
  getConfig,
  getHealth,
  getTasks,
  getWorldState,
  sendChat,
  updateConfig,
  type AuditLog,
  type ConfigResponse,
  type TaskListResponse,
  type WorldStateSummary,
} from '../lib/api/client';
import { connectRuntimeSocket, type RuntimeEvent } from '../lib/ws/runtimeSocket';

export async function bootstrapDesktopApp() {
  const root = document.getElementById('app');
  if (!root) {
    return;
  }

  root.innerHTML = App();

  let latestState = await getWorldState();
  let latestConfig = await getConfig();
  const health = await getHealth();
  const transport = connectRuntimeSocket((event) => {
    handleRuntimeEvent(event);
  });

  renderHealth(health.status);
  renderTransport(transport.enabled, transport.reason);
  renderWorldState(latestState);
  renderPresence(latestState);
  renderSettings(latestConfig);
  renderTasks(await getTasks());
  renderAudit(await getAuditLogs());

  bindComposer(async (text) => {
    appendMessage('user', text);
    setChatStatus('Waiting for runtime response...');
    const response = await sendChat(text);
    if (response.error) {
      appendMessage('system', `Error: ${response.error}`);
      setChatStatus('Runtime reported an error.');
      return;
    }
    setChatStatus(`Chat status: ${response.status}`);
    latestState = await getWorldState();
    renderWorldState(latestState);
    renderPresence(latestState);
    renderTasks(await getTasks());
    renderAudit(await getAuditLogs());
  });

  bindSettings(async () => {
    const proactiveToggle = document.getElementById('settings-proactive-toggle') as HTMLInputElement | null;
    const personaSelect = document.getElementById('settings-persona-select') as HTMLSelectElement | null;
    const safePolicySelect = document.getElementById('settings-safe-policy-select') as HTMLSelectElement | null;
    const externalPolicySelect = document.getElementById('settings-external-policy-select') as HTMLSelectElement | null;
    const sensitivePolicySelect = document.getElementById('settings-sensitive-policy-select') as HTMLSelectElement | null;
    const actionPolicySelect = document.getElementById('settings-action-policy-select') as HTMLSelectElement | null;
    const proactiveModeSelect = document.getElementById('settings-proactive-mode-select') as HTMLSelectElement | null;
    const patch = {
      proactive_enabled: proactiveToggle?.checked ?? false,
      persona_intensity: personaSelect?.value ?? 'normal',
      permission_safe_read_policy: safePolicySelect?.value ?? 'allow',
      permission_external_read_policy: externalPolicySelect?.value ?? 'ask',
      permission_sensitive_read_policy: sensitivePolicySelect?.value ?? 'ask',
      permission_action_policy: actionPolicySelect?.value ?? 'deny',
      proactive_mode: proactiveModeSelect?.value ?? 'balanced',
    };
    const result = await updateConfig(patch);
    if (result.updated) {
      latestConfig = result.config ?? latestConfig;
      renderSettings(latestConfig);
      renderAudit(await getAuditLogs());
      setChatStatus('Settings applied.');
    } else {
      setChatStatus('Failed to apply settings.');
    }
  });

  bindTaskActions();
}

void bootstrapDesktopApp();

function handleRuntimeEvent(event: RuntimeEvent) {
  if (event.type === 'presence.updated') {
    renderPresence({ presence: event.payload as WorldStateSummary['presence'] });
    return;
  }

  if (event.type === 'world_state.patched') {
    renderWorldState(event.payload as WorldStateSummary);
    renderPresence(event.payload as WorldStateSummary);
    return;
  }

  if (event.type === 'assistant.message.created') {
    const parts = Array.isArray((event.payload as { parts?: unknown[] }).parts)
      ? ((event.payload as { parts?: Array<{ type?: string; text?: string | null }> }).parts ?? [])
      : [];
    const text = parts.find((part) => part.type === 'text')?.text;
    if (text) {
      const source = typeof event.payload.source === 'string' ? event.payload.source : 'runtime';
      appendMessage(source === 'proactive' ? 'system' : 'assistant', source === 'proactive' ? `[proactive] ${text}` : text);
      setChatStatus(source === 'proactive' ? 'Proactive suggestion emitted.' : 'Assistant replied.');
    }
    return;
  }

  if (event.type === 'assistant.proactive.suggested') {
    setChatStatus('Ayria observed context and prepared a proactive suggestion.');
    void refreshAudit();
    return;
  }

  if (event.type === 'permission.requested') {
    setChatStatus(`Approval required for ${String(event.payload.tool_name ?? 'tool')}.`);
    void refreshTasks();
    void refreshAudit();
    return;
  }

  if (event.type === 'task.updated') {
    void refreshTasks();
    void refreshAudit();
    return;
  }

  if (event.type === 'tool.called') {
    setChatStatus(`Executing ${String(event.payload.tool_name ?? 'tool')}...`);
    return;
  }

  if (event.type === 'tool.result' || event.type === 'tool.failed' || event.type === 'config.updated') {
    void refreshAudit();
    if (event.type === 'config.updated') {
      void refreshConfig();
    }
    return;
  }

  if (event.type === 'events.dropped') {
    setChatStatus(`Event stream dropped ${(event.payload.dropped_count as number | undefined) ?? 0} event(s).`);
  }
}

function bindComposer(onSend: (text: string) => Promise<void>) {
  const sendButton = document.getElementById('chat-send-button');
  const input = document.getElementById('chat-input') as HTMLTextAreaElement | null;
  if (!sendButton || !input) {
    return;
  }

  sendButton.addEventListener('click', async () => {
    const text = input.value.trim();
    if (!text) {
      return;
    }
    input.value = '';
    await onSend(text);
  });
}

function bindSettings(onSave: () => Promise<void>) {
  const saveButton = document.getElementById('settings-save-button');
  if (!saveButton) {
    return;
  }
  saveButton.addEventListener('click', async () => {
    await onSave();
  });
}

function bindTaskActions() {
  const taskNode = document.getElementById('task-list');
  if (!taskNode) {
    return;
  }
  taskNode.addEventListener('click', async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLButtonElement)) {
      return;
    }
    const taskId = target.dataset.taskId;
    const decision = target.dataset.decision;
    if (!taskId || !decision) {
      return;
    }
    setChatStatus(`${decision === 'approve' ? 'Approving' : 'Rejecting'} task ${taskId}...`);
    const response = await decideTask(taskId, decision === 'approve');
    if (response.status) {
      setChatStatus(`Task ${taskId} ${response.status}.`);
    } else {
      setChatStatus(`Task ${taskId} decision failed.`);
    }
    await refreshTasks();
    await refreshAudit();
  });
}

function renderHealth(status: string) {
  const runtimeHealthNode = document.getElementById('runtime-health');
  if (runtimeHealthNode) {
    runtimeHealthNode.textContent = `Runtime: ${status}`;
  }
}

function renderTransport(enabled: boolean, reason?: string) {
  const transportNode = document.getElementById('transport-status');
  if (!transportNode) {
    return;
  }
  transportNode.textContent = enabled ? 'Events: websocket enabled' : `Events: disabled (${reason ?? 'unknown'})`;
}

function renderPresence(worldState: WorldStateSummary) {
  const presence = worldState.presence;
  const modeNode = document.getElementById('presence-status');
  const reasonNode = document.getElementById('presence-reason');
  const focusNode = document.getElementById('presence-focus');
  const cooldownNode = document.getElementById('presence-cooldown');

  if (modeNode) {
    modeNode.textContent = `Mode: ${presence?.mode ?? 'idle'}`;
  }
  if (reasonNode) {
    reasonNode.textContent = `Reason: ${presence?.reason ?? 'unknown'}`;
  }
  if (focusNode) {
    focusNode.textContent = `Focus: ${presence?.focus_label ?? worldState.active_window?.window_title ?? 'unknown'}`;
  }
  if (cooldownNode) {
    cooldownNode.textContent = `Cooldown: ${presence?.cooldown_remaining_seconds ?? 0}s`;
  }
}

function renderWorldState(worldState: WorldStateSummary) {
  const worldStateNode = document.getElementById('world-state');
  if (worldStateNode) {
    worldStateNode.textContent = JSON.stringify(worldState, null, 2);
  }
}

function renderSettings(config: ConfigResponse) {
  const proactiveNode = document.getElementById('settings-proactive');
  const providerNode = document.getElementById('settings-provider');
  const personaNode = document.getElementById('settings-persona');
  const proactiveToggle = document.getElementById('settings-proactive-toggle') as HTMLInputElement | null;
  const personaSelect = document.getElementById('settings-persona-select') as HTMLSelectElement | null;
  const safePolicySelect = document.getElementById('settings-safe-policy-select') as HTMLSelectElement | null;
  const externalPolicySelect = document.getElementById('settings-external-policy-select') as HTMLSelectElement | null;
  const sensitivePolicySelect = document.getElementById('settings-sensitive-policy-select') as HTMLSelectElement | null;
  const actionPolicySelect = document.getElementById('settings-action-policy-select') as HTMLSelectElement | null;
  const proactiveModeSelect = document.getElementById('settings-proactive-mode-select') as HTMLSelectElement | null;

  if (proactiveNode) {
    proactiveNode.textContent = `Proactive: ${config.proactive_enabled ? 'enabled' : 'disabled'} (${config.proactive_mode ?? 'balanced'})`;
  }
  if (providerNode) {
    providerNode.textContent = `Provider: ${config.default_provider ?? 'local-first'} (${config.capability_model ?? 'unknown'})`;
  }
  if (personaNode) {
    personaNode.textContent = `Persona intensity: ${config.persona_intensity ?? 'normal'}`;
  }
  if (proactiveToggle) {
    proactiveToggle.checked = Boolean(config.proactive_enabled);
  }
  if (personaSelect && config.persona_intensity) {
    personaSelect.value = config.persona_intensity;
  }
  if (safePolicySelect && config.permission_safe_read_policy) {
    safePolicySelect.value = config.permission_safe_read_policy;
  }
  if (externalPolicySelect && config.permission_external_read_policy) {
    externalPolicySelect.value = config.permission_external_read_policy;
  }
  if (sensitivePolicySelect && config.permission_sensitive_read_policy) {
    sensitivePolicySelect.value = config.permission_sensitive_read_policy;
  }
  if (actionPolicySelect && config.permission_action_policy) {
    actionPolicySelect.value = config.permission_action_policy;
  }
  if (proactiveModeSelect && config.proactive_mode) {
    proactiveModeSelect.value = config.proactive_mode;
  }
}

function renderTasks(taskResponse: TaskListResponse) {
  const taskNode = document.getElementById('task-list');
  if (!taskNode) {
    return;
  }
  const items = taskResponse.items ?? [];
  if (!items.length) {
    taskNode.textContent = 'No tasks yet.';
    return;
  }
  taskNode.innerHTML = items
    .slice(0, 6)
    .map((item) => {
      const toolName = typeof item.input_payload?.tool_name === 'string' ? item.input_payload.tool_name : '';
      const reason = typeof item.output_payload?.reason === 'string' ? item.output_payload.reason : '';
      const controls =
        item.status === 'awaiting_user'
          ? `<div>
              <button type="button" data-task-id="${item.id}" data-decision="approve">Approve</button>
              <button type="button" data-task-id="${item.id}" data-decision="reject">Reject</button>
            </div>`
          : '';
      return `<div data-task-id="${item.id}">
        <strong>${item.type}</strong> · ${item.status} · ${item.updated_at}
        ${toolName ? `<div>Tool: ${toolName}</div>` : ''}
        ${reason ? `<div>Reason: ${reason}</div>` : ''}
        ${controls}
      </div>`;
    })
    .join('');
}

function renderAudit(items: AuditLog[]) {
  const auditNode = document.getElementById('audit-log');
  if (!auditNode) {
    return;
  }
  if (!items.length) {
    auditNode.textContent = 'No audit records yet.';
    return;
  }
  auditNode.innerHTML = items
    .slice(0, 8)
    .map((item) => `<div data-audit-id="${item.id}">${item.category} · ${item.decision} · ${item.summary}</div>`)
    .join('');
}

function appendMessage(role: 'user' | 'assistant' | 'system', text: string) {
  const container = document.getElementById('chat-messages');
  if (!container) {
    return;
  }
  if (container.textContent === 'No messages yet.') {
    container.textContent = '';
  }
  const line = document.createElement('div');
  line.setAttribute('data-role', role);
  line.textContent = `${role}: ${text}`;
  container.appendChild(line);
}

function setChatStatus(text: string) {
  const statusNode = document.getElementById('chat-status');
  if (statusNode) {
    statusNode.textContent = text;
  }
}

async function refreshAudit() {
  renderAudit(await getAuditLogs());
}

async function refreshTasks() {
  renderTasks(await getTasks());
}

async function refreshConfig() {
  renderSettings(await getConfig());
}
