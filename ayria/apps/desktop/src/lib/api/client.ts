/**
 * Typed HTTP client placeholder.
 *
 * Keep request construction here so feature code stays simple.
 * This is the preferred place for:
 * - base URL setup
 * - request/response typing
 * - auth token injection if needed later
 * - retry policy for non-destructive calls
 */

export type HealthResponse = {
  status: 'ok' | 'degraded' | 'error';
  service?: string;
  version?: string;
};

export type SendChatResponse = {
  status: 'completed' | 'degraded' | 'failed';
  inference_mode?: string;
  assistant_message?: {
    parts?: Array<{
      type?: string;
      text?: string | null;
    }>;
  };
  error?: string;
};

export type WorldStateSummary = {
  active_window?: {
    app_name?: string;
    window_title?: string;
    url?: string | null;
  } | null;
  presence?: {
    mode?: string;
    proactive_allowed?: boolean;
    reason?: string | null;
    focus_label?: string | null;
    cooldown_remaining_seconds?: number;
  } | null;
  current_task_hint?: string | null;
};

export type ConfigResponse = {
  default_provider?: string;
  capability_model?: string;
  proactive_enabled?: boolean;
  proactive_mode?: string;
  persona_intensity?: string;
  permission_safe_read_policy?: string;
  permission_external_read_policy?: string;
  permission_sensitive_read_policy?: string;
  permission_action_policy?: string;
};

export type AuditLog = {
  id: string;
  category: string;
  action: string;
  decision: string;
  summary: string;
  metadata?: Record<string, unknown>;
  created_at: string;
};

export type TaskListResponse = {
  items?: Array<{
    id: string;
    type: string;
    status: string;
    updated_at: string;
    input_payload?: Record<string, unknown>;
    output_payload?: Record<string, unknown> | null;
  }>;
};

const API_BASE = 'http://127.0.0.1:8000/api/v1';

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    return { status: 'error' };
  }
  return (await response.json()) as HealthResponse;
}

export async function getWorldState(): Promise<WorldStateSummary> {
  const response = await fetch(`${API_BASE}/world-state`);
  if (!response.ok) {
    return {};
  }
  return (await response.json()) as WorldStateSummary;
}

export async function sendChat(text: string): Promise<SendChatResponse> {
  const response = await fetch(`${API_BASE}/chat/send`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text, image_paths: [] }),
  });
  if (!response.ok) {
    return { status: 'failed', error: `http_${response.status}` };
  }
  return (await response.json()) as SendChatResponse;
}

export async function getConfig(): Promise<ConfigResponse> {
  const response = await fetch(`${API_BASE}/config`);
  if (!response.ok) {
    return {};
  }
  return (await response.json()) as ConfigResponse;
}

export async function updateConfig(patch: Record<string, unknown>): Promise<{ updated: boolean; config?: ConfigResponse; diff?: Record<string, unknown> }> {
  const response = await fetch(`${API_BASE}/config`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(patch),
  });
  if (!response.ok) {
    return { updated: false };
  }
  return (await response.json()) as { updated: boolean; config?: ConfigResponse; diff?: Record<string, unknown> };
}

export async function getAuditLogs(): Promise<AuditLog[]> {
  const response = await fetch(`${API_BASE}/audit/logs`);
  if (!response.ok) {
    return [];
  }
  const body = (await response.json()) as { items?: AuditLog[] };
  return body.items ?? [];
}

export async function getTasks(): Promise<TaskListResponse> {
  const response = await fetch(`${API_BASE}/tasks`);
  if (!response.ok) {
    return { items: [] };
  }
  return (await response.json()) as TaskListResponse;
}

export async function decideTask(taskId: string, approve: boolean): Promise<{ status?: string; task?: Record<string, unknown>; result?: Record<string, unknown> }> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/decision`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ approve }),
  });
  if (!response.ok) {
    return {};
  }
  return (await response.json()) as { status?: string; task?: Record<string, unknown>; result?: Record<string, unknown> };
}
