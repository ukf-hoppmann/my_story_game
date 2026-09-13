import { ApiError, reportFrontendError } from "./client";

/** Serializable error shape used across every RTK Query endpoint. */
export interface QueryError {
  status: number;
  code: string;
  message: string;
}

/** TASK-030's three error categories, encoded as `QueryError.code`:
 *  - a real backend `ApiError` keeps its own `code`/`message` (shown to the
 *    user as-is via `ErrorBanner`) — except `401`, which becomes
 *    `SESSION_EXPIRED_CODE`;
 *  - anything else never reached the backend as a typed error at all
 *    (network failure, JSON-parse failure, a synchronous JS exception) —
 *    that becomes `TOOLING_ERROR_CODE` and is reported to the backend's
 *    diagnostics endpoint, fire-and-forget, so it stays visible without
 *    needing an individual user's browser console. */
export const SESSION_EXPIRED_CODE = "session_expired";
export const TOOLING_ERROR_CODE = "tooling_error";

/** Normalizes anything a client.ts call can throw into a QueryError, so RTK
 *  Query endpoints never leak a raw exception into the Redux store.
 *
 *  `source` identifies the call site (e.g. `"apiSlice.listRuns"`) purely for
 *  the tooling-error report below — it never affects the returned
 *  `QueryError`. A `401` is deliberately not reported: at that point no
 *  valid token remains to authenticate the report with, and the frontend
 *  already handles it as a forced re-login (see `ErrorBanner`), which is
 *  self-explanatory without a backend log entry. */
export function toQueryError(error: unknown, source: string): QueryError {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return { status: 401, code: SESSION_EXPIRED_CODE, message: error.message };
    }
    return { status: error.status, code: error.code, message: error.message };
  }

  const message = error instanceof Error ? error.message : String(error);
  // Fire-and-forget: a failing report must never cause a second
  // user-visible failure on top of the one already being handled here.
  void reportFrontendError({
    source,
    message,
    url: typeof window !== "undefined" ? window.location.href : undefined,
    user_agent: typeof navigator !== "undefined" ? navigator.userAgent : undefined,
  }).catch(() => {});

  return { status: 0, code: TOOLING_ERROR_CODE, message };
}
