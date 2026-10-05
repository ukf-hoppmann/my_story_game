import { Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { isAdmin } from "../api/auth";

/**
 * Layout route for pages only the admin may see. Nest it inside
 * `RequireAuth`, so the Keycloak session (and with it the role) exists.
 * This is a convenience: the backend answers 403 to every admin request
 * from anyone else.
 */
export function RequireAdmin() {
  const { t } = useTranslation();

  if (!isAdmin()) {
    return (
      <div style={{ padding: 40, color: "var(--wine-bright)", fontFamily: "var(--font-ui)" }}>
        {t("requireAdmin.forbidden")}
      </div>
    );
  }

  return <Outlet />;
}
