import type {
  ApiErrorBody,
  ConfirmRunProposalRequest,
  GameDocument,
  PlayTurnRequest,
  ProposeRunRequest,
  RunProposal,
  RunSummaryList,
  TurnResult,
} from "./types";

const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/** Typed failure carrying the backend's error envelope ({error, detail, ...}). */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly body: ApiErrorBody;

  constructor(status: number, body: ApiErrorBody) {
    super(body.detail || body.error);
    this.status = status;
    this.code = body.error;
    this.body = body;
  }
}

// Single injection point for a future auth header (Keycloak). Nothing
// populates this yet — the backend uses one fixed dev identity today.
let authHeaderProvider: (() => Record<string, string>) | null = null;

export function setAuthHeaderProvider(
  provider: (() => Record<string, string>) | null,
): void {
  authHeaderProvider = provider;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(authHeaderProvider ? authHeaderProvider() : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let body: ApiErrorBody;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      body = { error: "unknown_error", detail: response.statusText };
    }
    throw new ApiError(response.status, body);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function checkHealth(): Promise<{ status: string }> {
  return request("/health");
}

export async function listRuns(): Promise<RunSummaryList> {
  return request("/api/v1/runs");
}

export async function loadRun(
  runId: string,
  revision?: number,
): Promise<GameDocument> {
  const query = revision ? `?revision=${revision}` : "";
  return request(`/api/v1/runs/${runId}${query}`);
}

export async function proposeRun(
  payload: ProposeRunRequest,
): Promise<RunProposal> {
  return request("/api/v1/runs/proposals", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function confirmRun(
  payload: ConfirmRunProposalRequest,
): Promise<GameDocument> {
  return request("/api/v1/runs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function startPlaythrough(runId: string): Promise<GameDocument> {
  return request(`/api/v1/runs/${runId}/playthroughs`, { method: "POST" });
}

export async function playTurn(
  runId: string,
  payload: PlayTurnRequest,
): Promise<TurnResult> {
  return request(`/api/v1/runs/${runId}/turns`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
