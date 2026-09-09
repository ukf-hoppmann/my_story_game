/**
 * Keycloak login/session handling, wired into the API client's reserved
 * auth-header injection point (see `setAuthHeaderProvider` in `client.ts`) —
 * nothing else in the app needs to know a token exists.
 */
import Keycloak from "keycloak-js";
import { setAuthHeaderProvider } from "./client";

const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL ?? "http://auth.storygame.localhost",
  realm: import.meta.env.VITE_KEYCLOAK_REALM ?? "story-game",
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? "story-game-frontend",
});

/**
 * Redirects to Keycloak's login page if there's no session yet, otherwise
 * resolves once a valid token is available. Not called at app boot — the
 * Landing page (`/`) is meant to be reachable without a login redirect, so
 * this only runs when a protected route is actually entered (see
 * `ensureAuth` and `RequireAuth`).
 */
export async function initAuth(): Promise<void> {
  await keycloak.init({ onLoad: "login-required", pkceMethod: "S256" });

  setAuthHeaderProvider(() => ({ Authorization: `Bearer ${keycloak.token}` }));

  // Refresh proactively; if that ever fails (e.g. the session expired for
  // real), there is no good in-app recovery — send the user back through
  // login rather than letting requests silently start failing with 401.
  keycloak.onTokenExpired = () => {
    keycloak.updateToken(30).catch(() => keycloak.login());
  };
}

let authPromise: Promise<void> | null = null;

/**
 * Lazily runs `initAuth()` on first call and caches the in-flight/resolved
 * promise, so multiple protected routes mounting (or React StrictMode's
 * double-invoked effects) only ever trigger one login flow — Keycloak's
 * client throws if `init()` runs twice.
 */
export function ensureAuth(): Promise<void> {
  if (!authPromise) {
    authPromise = initAuth();
  }
  return authPromise;
}

/** Test-only: clears the cached auth promise so each test starts fresh. */
export function resetAuthForTests(): void {
  authPromise = null;
}

/** The logged-in user's display name, for the "who am I" corner of the UI. */
export function currentUsername(): string | undefined {
  return keycloak.tokenParsed?.preferred_username as string | undefined;
}

export function logout(): void {
  keycloak.logout();
}
