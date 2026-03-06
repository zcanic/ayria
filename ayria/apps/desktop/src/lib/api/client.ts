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

export type WorldStateSummary = {
  active_window?: {
    app_name?: string;
    window_title?: string;
    url?: string | null;
  } | null;
  presence?: {
    mode?: string;
    proactive_allowed?: boolean;
  } | null;
  current_task_hint?: string | null;
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
