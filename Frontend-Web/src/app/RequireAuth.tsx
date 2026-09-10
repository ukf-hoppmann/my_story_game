import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ensureAuth } from "../api/auth";

type AuthGateStatus = "loading" | "ready" | "error";

/**
 * Route-level auth gate (Schritt 5b): wrap protected routes with this as a
 * layout route so only *they* trigger the Keycloak login-required redirect.
 * The Landing page ("/") stays outside this gate and is reachable without
 * ever calling `ensureAuth()`.
 */
export function RequireAuth() {
  const { t } = useTranslation();
  const [status, setStatus] = useState<AuthGateStatus>("loading");

  useEffect(() => {
    let cancelled = false;
    ensureAuth()
      .then(() => {
        if (!cancelled) {
          setStatus("ready");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (status === "loading") {
    return (
      <div style={{ padding: 40, color: "var(--text-muted)", fontFamily: "var(--font-ui)" }}>
        {t("requireAuth.checking")}
      </div>
    );
  }

  if (status === "error") {
    return (
      <div style={{ padding: 40, color: "var(--wine-bright)", fontFamily: "var(--font-ui)" }}>
        {t("requireAuth.failed")}
      </div>
    );
  }

  return <Outlet />;
}
