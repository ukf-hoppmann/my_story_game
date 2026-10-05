import type {
  AdminModelOverview,
  AdminModelSetting,
  AdminModelSettingList,
  AdminModelTask,
  AdminPromptKind,
  AdminPromptList,
  AdminPromptVersion,
  AdminPromptVersionList,
  CreatePromptOptionRequest,
  ApiErrorBody,
  ConfirmRunProposalRequest,
  CreateSceneImageRequest,
  GameDocument,
  GameState,
  PlayTurnRequest,
  ProposeRunRequest,
  PromptProfileCatalog,
  ResetModelSettingsRequest,
  PromptOptionRef,
  RemovalResult,
  RemovePromptOptionsRequest,
  ResetPromptsRequest,
  RunProposal,
  RunSummaryList,
  SaveModelSettingRequest,
  SavePromptTextRequest,
  SceneImage,
  SceneImageCapabilities,
  SceneImageList,
  TurnResult,
  UpdateConfigurationRequest,
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

// Single injection point for the auth header (Keycloak), wired up by
// `api/auth.ts`. Kept as a plain module-level seam so the request layer
// itself has no dependency on any particular auth library.
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

/** Public catalog of selectable story-creation options (genre, tone, ...).
 *  Requires no auth — used to render the wizard before/without a run. */
export async function fetchPromptProfileCatalog(): Promise<PromptProfileCatalog> {
  return request("/api/v1/prompt-profile");
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

export async function updateConfiguration(
  runId: string,
  payload: UpdateConfigurationRequest,
): Promise<GameState> {
  return request(`/api/v1/runs/${runId}/configuration`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
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

/** Whether scene images are enabled on this installation, and which models
 *  exist. Always answers 200 — a disabled feature is `enabled: false`. */
export async function fetchSceneImageCapabilities(): Promise<SceneImageCapabilities> {
  return request("/api/v1/scene-images/capabilities");
}

export async function listSceneImages(runId: string): Promise<SceneImageList> {
  return request(`/api/v1/runs/${runId}/scene-images`);
}

/** Starts a generation; answers 202 at once with the still-pending image. */
export async function createSceneImage(
  runId: string,
  payload: CreateSceneImageRequest,
): Promise<SceneImage> {
  return request(`/api/v1/runs/${runId}/scene-images`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** The image bytes need the auth header, so an `<img src>` cannot load them
 *  directly: fetch them here and let the caller make an object URL. */
export async function fetchSceneImageBlob(runId: string, imageId: string): Promise<Blob> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/runs/${runId}/scene-images/${imageId}/content`,
    { headers: authHeaderProvider ? authHeaderProvider() : {} },
  );
  if (!response.ok) {
    let body: ApiErrorBody;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      body = { error: "unknown_error", detail: response.statusText };
    }
    throw new ApiError(response.status, body);
  }
  return response.blob();
}

/** A frontend-side failure that never reached the backend as a typed
 *  `ApiError` (network failure, JSON-parse failure, a synchronous JS
 *  exception before a request was dispatched) — see `queryError.ts`
 *  (TASK-030). Uses the same authenticated `request()` as every other call;
 *  deliberately excludes `401`s, which the frontend handles as a forced
 *  re-login instead (see `ErrorBanner`). */
export interface FrontendErrorReport {
  source: string;
  message: string;
  url?: string;
  user_agent?: string;
}

export async function reportFrontendError(payload: FrontendErrorReport): Promise<void> {
  return request("/api/v1/diagnostics/frontend-errors", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Admin only (backend answers 403 without the `admin` role): the active
 *  system prompts, each with where its current text came from. */
export async function listAdminPrompts(): Promise<AdminPromptList> {
  return request("/api/v1/admin/prompts");
}

/** Every version of one prompt entry, newest first. */
export async function fetchPromptHistory(
  kind: AdminPromptKind,
  key: string,
): Promise<AdminPromptVersionList> {
  const query = new URLSearchParams({ kind, key });
  return request(`/api/v1/admin/prompts/history?${query.toString()}`);
}

/** Saves the text as the entry's new active version; the old one stays in the history. */
export async function savePromptText(
  payload: SavePromptTextRequest,
): Promise<AdminPromptVersion> {
  return request("/api/v1/admin/prompts", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

/** Adds a selectable option (genre, tone or prose style); it shows up in the wizard at once. */
export async function createPromptOption(
  payload: CreatePromptOptionRequest,
): Promise<AdminPromptVersion> {
  return request("/api/v1/admin/prompts/options", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

function optionQuery(payload: PromptOptionRef): string {
  return new URLSearchParams({ category: payload.category, option_id: payload.option_id }).toString();
}

/** Moves an option added in the UI to the trash; refused for shipped options and ones a story still uses. */
export async function archivePromptOption(payload: PromptOptionRef): Promise<void> {
  return request(`/api/v1/admin/prompts/options?${optionQuery(payload)}`, { method: "DELETE" });
}

/** The options in the trash, newest version of each. */
export async function listArchivedPromptOptions(): Promise<AdminPromptVersionList> {
  return request("/api/v1/admin/prompts/options/archived");
}

/** Takes an option out of the trash. */
export async function restorePromptOption(payload: PromptOptionRef): Promise<void> {
  return request("/api/v1/admin/prompts/options/restore", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Deletes an option in the trash for good, with its history. */
export async function purgePromptOption(payload: PromptOptionRef): Promise<void> {
  return request(`/api/v1/admin/prompts/options/archived?${optionQuery(payload)}`, { method: "DELETE" });
}

/** Archives or purges several options; every option gets its own outcome. */
export async function removePromptOptions(
  payload: RemovePromptOptionsRequest,
): Promise<RemovalResult> {
  return request("/api/v1/admin/prompts/options/removal", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Re-applies the shipped original as a new version, for one entry or (with `{}`) all. */
export async function resetPrompts(
  payload: ResetPromptsRequest,
): Promise<AdminPromptVersionList> {
  return request("/api/v1/admin/prompts/reset", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Admin only: the active model choice of every task plus the catalog models
 *  selectable for each. */
export async function listAdminModels(): Promise<AdminModelOverview> {
  return request("/api/v1/admin/models");
}

/** Every version of one task's model choice, newest first. */
export async function fetchModelHistory(task: AdminModelTask): Promise<AdminModelSettingList> {
  const query = new URLSearchParams({ task });
  return request(`/api/v1/admin/models/history?${query.toString()}`);
}

/** Saves the choice as the task's new active version; the old one stays in the history. */
export async function saveModelSetting(
  payload: SaveModelSettingRequest,
): Promise<AdminModelSetting> {
  return request("/api/v1/admin/models", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

/** Re-applies the shipped original as a new version, for one task or (with `{}`) all. */
export async function resetModelSettings(
  payload: ResetModelSettingsRequest,
): Promise<AdminModelSettingList> {
  return request("/api/v1/admin/models/reset", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
