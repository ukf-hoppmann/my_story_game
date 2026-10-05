import { useEffect, useState } from "react";
import { checkSession, currentUsername, isAdmin } from "../api/auth";

export type Session =
  | { status: "checking" }
  | { status: "anonymous" }
  | { status: "authenticated"; username: string | undefined; admin: boolean };

/**
 * The signed-in state for the app chrome (header). Runs the silent
 * `check-sso` once on mount, so it never redirects; a failing check (e.g.
 * Keycloak unreachable) counts as "anonymous" — protected routes report that
 * error themselves through `RequireAuth`.
 */
export function useSession(): Session {
  const [session, setSession] = useState<Session>({ status: "checking" });

  useEffect(() => {
    let cancelled = false;
    checkSession()
      .then((authenticated) => authenticated)
      .catch(() => false)
      .then((authenticated) => {
        if (cancelled) {
          return;
        }
        setSession(
          authenticated
            ? { status: "authenticated", username: currentUsername(), admin: isAdmin() }
            : { status: "anonymous" },
        );
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return session;
}
