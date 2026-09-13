import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { login } from "../../api/auth";
import { SESSION_EXPIRED_CODE, TOOLING_ERROR_CODE, type QueryError } from "../../api/queryError";

export interface ErrorBannerProps {
  /** An RTK Query error state (already normalized by `toQueryError`), or
   *  any other falsy/error-shaped value a screen passes straight through
   *  (e.g. `catalogError`, `startState.error`). Renders nothing if falsy. */
  error: unknown;
  /** Screen-specific overrides for backend codes that need dedicated
   *  recovery copy (e.g. `Play.tsx`'s `run_not_active`/`revision_conflict`),
   *  taking priority over the raw backend message. */
  knownCodes?: Record<string, string>;
  /** Shown only when the error carries no usable message at all. */
  fallbackKey: string;
  /** Applied to the banner's own wrapping `<p>`. Ignored when `bare`. */
  className?: string;
  /** Renders inline content only, with no wrapping element, for a screen
   *  that already owns its own banner layout (e.g. `Play.tsx`'s
   *  `<div className="play-error-banner">…</div>` with its own reload
   *  button). */
  bare?: boolean;
}

function isQueryErrorLike(error: unknown): error is QueryError {
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    typeof (error as { code: unknown }).code === "string"
  );
}

/**
 * TASK-030's single, reusable error display: classifies an already-typed
 * `QueryError` into one of three cases —
 * `session_expired` (forced re-login, never a raw backend message),
 * `tooling_error` (generic "logged" text, the actual message already went
 * to the backend via `toQueryError`), or a genuine backend error (shows the
 * backend's own `message`, since TASK-030 requires the real explanation
 * rather than one fixed generic string per screen) — falling back to
 * `fallbackKey` only when there is no message to show at all.
 */
export function ErrorBanner({ error, knownCodes = {}, fallbackKey, className, bare }: ErrorBannerProps) {
  const { t } = useTranslation();
  if (!error) {
    return null;
  }

  const code = isQueryErrorLike(error) ? error.code : undefined;
  const message = isQueryErrorLike(error) ? error.message : undefined;

  let content: ReactNode;
  if (code === SESSION_EXPIRED_CODE) {
    content = (
      <>
        {t("errors.sessionExpired")}{" "}
        <button type="button" className="error-banner-relogin" onClick={() => login()}>
          {t("common.reLogin")}
        </button>
      </>
    );
  } else if (code === TOOLING_ERROR_CODE) {
    content = t("errors.toolingGeneric");
  } else if (code && knownCodes[code]) {
    content = t(knownCodes[code]);
  } else if (message) {
    content = t("errors.backendError", { message });
  } else {
    content = t(fallbackKey);
  }

  if (bare) {
    return <>{content}</>;
  }
  return <p className={className}>{content}</p>;
}
