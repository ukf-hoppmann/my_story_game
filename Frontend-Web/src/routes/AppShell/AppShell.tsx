import { Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ensureAuth, logout } from "../../api/auth";
import { useSession } from "../../app/useSession";
import { AppHeader } from "../../components/AppHeader/AppHeader";
import { HeaderMenu } from "../../components/AppHeader/HeaderMenu";
import { Button } from "../../components/Button/Button";
import { SignInIcon, SignOutIcon } from "../../icons";
import "./AppShell.css";

/**
 * Root layout route wrapping every page, including Landing (which sits
 * outside `RequireAuth`). Keeps `AppHeader` persistently visible so there is
 * always a way back to Landing, independent of the current route or the
 * auth-gate status of its children.
 *
 * The header's right side follows the session, found by a silent
 * `check-sso` (no redirect): anonymous visitors get "Anmelden" (runs
 * `ensureAuth()`, which redirects to Keycloak's login); signed-in users get
 * the navigation menu and "Abmelden".
 */
export function AppShell() {
  const { t } = useTranslation();
  const session = useSession();

  return (
    <div className="app-shell">
      <AppHeader
        right={
          session.status === "anonymous" ? (
            <Button variant="ghost" icon={<SignInIcon />} onClick={() => void ensureAuth()}>
              {t("landing.signIn")}
            </Button>
          ) : session.status === "authenticated" ? (
            <>
              <HeaderMenu username={session.username} admin={session.admin} />
              <Button variant="ghost" icon={<SignOutIcon />} onClick={logout}>
                {t("appHeader.signOut")}
              </Button>
            </>
          ) : null
        }
      />
      <div className="app-content">
        <Outlet />
      </div>
    </div>
  );
}
