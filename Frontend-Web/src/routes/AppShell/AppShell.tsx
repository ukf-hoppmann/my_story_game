import { Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AppHeader } from "../../components/AppHeader/AppHeader";
import { Button } from "../../components/Button/Button";
import { SignInIcon } from "../../icons";
import "./AppShell.css";

/**
 * Root layout route wrapping every page, including Landing (which sits
 * outside `RequireAuth`). Keeps `AppHeader` persistently visible so there is
 * always a way back to Landing, independent of the current route or the
 * auth-gate status of its children.
 *
 * The sign-in action only makes sense on Landing (every other route is
 * already behind `RequireAuth`), so it's added to the header's right slot
 * here rather than living in each page.
 */
export function AppShell() {
  const location = useLocation();
  const { t } = useTranslation();
  const isLanding = location.pathname === "/";

  return (
    <div className="app-shell">
      <AppHeader
        right={
          isLanding && (
            <Button variant="ghost" icon={<SignInIcon />}>
              {t("landing.signIn")}
            </Button>
          )
        }
      />
      <div className="app-content">
        <Outlet />
      </div>
    </div>
  );
}
