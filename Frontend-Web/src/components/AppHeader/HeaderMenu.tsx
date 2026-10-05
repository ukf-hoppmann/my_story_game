import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { MenuIcon } from "../../icons";

export interface HeaderMenuProps {
  username: string | undefined;
  /** Adds the admin-only entries (settings). */
  admin: boolean;
}

/**
 * Hamburger menu of the signed-in header: navigation to the main screens,
 * plus the admin-only settings. Closes on selection, Escape, and a click
 * outside.
 */
export function HeaderMenu({ username, admin }: HeaderMenuProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onPointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const close = () => setOpen(false);

  return (
    <div className="header-menu" ref={rootRef}>
      <button
        type="button"
        className="header-menu-toggle"
        aria-label={t("appHeader.menu")}
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <MenuIcon />
      </button>
      {open && (
        <nav className="header-menu-panel" aria-label={t("appHeader.menu")}>
          {username && <div className="header-menu-user">{username}</div>}
          <Link to="/library" onClick={close}>
            {t("common.yourStories")}
          </Link>
          <Link to="/new" onClick={close}>
            {t("library.newStory")}
          </Link>
          {admin && (
            <Link to="/settings" onClick={close}>
              {t("library.settings")}
            </Link>
          )}
        </nav>
      )}
    </div>
  );
}
