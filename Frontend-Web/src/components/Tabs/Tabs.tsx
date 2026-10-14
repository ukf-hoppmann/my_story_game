import type { KeyboardEvent, ReactNode } from "react";
import "./Tabs.css";

export interface TabItem {
  id: string;
  label: string;
  /** Optional item count shown as a small badge after the label. */
  count?: number;
}

export interface TabsProps {
  tabs: TabItem[];
  activeId: string;
  onChange: (id: string) => void;
  /** Distinguishes the element ids when tab bars are nested. */
  idPrefix?: string;
  /** Content of the active tab. */
  children: ReactNode;
}

/**
 * Tab bar with the content of the active tab below it. Arrow keys move
 * between tabs (roving tabindex), as the ARIA tabs pattern asks.
 */
export function Tabs({ tabs, activeId, onChange, idPrefix = "tab", children }: TabsProps) {
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (step === 0) {
      return;
    }
    event.preventDefault();
    const index = tabs.findIndex((tab) => tab.id === activeId);
    const next = tabs[(index + step + tabs.length) % tabs.length];
    onChange(next.id);
    document.getElementById(`${idPrefix}-${next.id}`)?.focus();
  };

  return (
    <div className="tabs">
      <div className="tabs-bar" role="tablist" onKeyDown={onKeyDown}>
        {tabs.map((tab) => {
          const active = tab.id === activeId;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              id={`${idPrefix}-${tab.id}`}
              aria-selected={active}
              aria-controls={`${idPrefix}-panel-${tab.id}`}
              tabIndex={active ? 0 : -1}
              className={active ? "tabs-tab tabs-tab--active" : "tabs-tab"}
              onClick={() => onChange(tab.id)}
            >
              {tab.label}
              {tab.count !== undefined && <span className="tabs-count">{tab.count}</span>}
            </button>
          );
        })}
      </div>
      <div
        className="tabs-panel"
        role="tabpanel"
        id={`${idPrefix}-panel-${activeId}`}
        aria-labelledby={`${idPrefix}-${activeId}`}
      >
        {children}
      </div>
    </div>
  );
}
