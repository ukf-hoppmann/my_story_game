import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CompassIcon } from "../../icons";
import "./AppHeader.css";

export interface AppHeaderProps {
  /** Optional content for the header's right side, e.g. Landing's sign-in action. */
  right?: ReactNode;
}

/**
 * Persistent top bar shown on every route via `AppShell`. The brand mark
 * always links back to "/" so there is a way back to the Landing page from
 * anywhere in the app, regardless of the current screen or auth state.
 */
export function AppHeader({ right }: AppHeaderProps) {
  const { t } = useTranslation();

  return (
    <header className="app-header">
      <Link to="/" className="app-header-brand">
        <CompassIcon />
        <span>{t("appHeader.brand")}</span>
      </Link>
      {right && <div className="app-header-right">{right}</div>}
    </header>
  );
}
