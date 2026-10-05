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

let sessionPromise: Promise<boolean> | null = null;

/**
 * Asks Keycloak whether a session already exists, without redirecting the
 * page: `check-sso` runs in a hidden iframe (`silent-check-sso.html`) and
 * only reports the outcome. Used at app start so the Landing page can show
 * the right header (sign-in vs. menu + sign-out) without forcing a login.
 * Resolves `true` when a user is signed in; the API client's auth header and
 * proactive token refresh are wired up in that case. The result is cached
 * (see `resetAuthForTests`) because Keycloak's client throws if `init()`
 * runs twice.
 */
export function checkSession(): Promise<boolean> {
  if (!sessionPromise) {
    sessionPromise = initSession();
  }
  return sessionPromise;
}

async function initSession(): Promise<boolean> {
  const authenticated = await keycloak.init({
    onLoad: "check-sso",
    silentCheckSsoRedirectUri: `${window.location.origin}/silent-check-sso.html`,
    pkceMethod: "S256",
  });
  if (!authenticated) {
    return false;
  }

  setAuthHeaderProvider(() => ({ Authorization: `Bearer ${keycloak.token}` }));

  // Refresh proactively; if that ever fails (e.g. the session expired for
  // real), there is no good in-app recovery — send the user back through
  // login rather than letting requests silently start failing with 401.
  keycloak.onTokenExpired = () => {
    keycloak.updateToken(30).catch(() => keycloak.login());
  };
  return true;
}

/**
 * Resolves once a valid session exists, redirecting to Keycloak's login page
 * first if there is none. Only protected routes and the sign-in action call
 * this (see `RequireAuth`); the Landing page stays reachable without a
 * login redirect. In the redirect case the promise never settles, because
 * the page is leaving anyway and must not render protected content.
 */
export async function ensureAuth(): Promise<void> {
  if (await checkSession()) {
    return;
  }
  await keycloak.login();
  await new Promise<never>(() => {});
}

/** Test-only: clears the cached auth promise so each test starts fresh. */
export function resetAuthForTests(): void {
  sessionPromise = null;
}

/** The logged-in user's display name, for the "who am I" corner of the UI. */
export function currentUsername(): string | undefined {
  return keycloak.tokenParsed?.preferred_username as string | undefined;
}

/** Name of the Keycloak realm role that unlocks the settings. The backend
 *  enforces it on every admin request; this only decides what the UI shows. */
const ADMIN_ROLE = "admin";

/** Whether the logged-in user holds the admin realm role. `false` before
 *  `ensureAuth()` has resolved. */
export function isAdmin(): boolean {
  return keycloak.hasRealmRole(ADMIN_ROLE);
}

/** Ends the Keycloak session and returns to the Landing page. */
export function logout(): void {
  keycloak.logout({ redirectUri: `${window.location.origin}/` });
}

/** Redirects to Keycloak's login page. Used by `ErrorBanner`'s re-login
 *  action after a `session_expired` (`401`) error (TASK-030) — a plain
 *  redirect back into the login flow, distinct from `logout()`. */
export function login(): void {
  keycloak.login();
}
