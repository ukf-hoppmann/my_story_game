import { useLayoutEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  usePromptHistoryQuery,
  useListAdminPromptsQuery,
  useRemovePromptOptionMutation,
  useResetPromptsMutation,
  useSavePromptTextMutation,
} from "../../api/apiSlice";
import type { AdminPromptKind, AdminPromptVersion } from "../../api/types";
import { Accordion } from "../../components/Accordion/Accordion";
import { Button } from "../../components/Button/Button";
import { ErrorBanner } from "../../components/ErrorBanner/ErrorBanner";
import { Tabs } from "../../components/Tabs/Tabs";
import { PlusIcon } from "../../icons";
import { formatOptionLabel } from "../../utils/formatOptionLabel";
import { ModelSettings } from "./ModelSettings";
import { NewOptionForm } from "./NewOptionForm";
import "./Settings.css";


function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function PromptHistory({ kind, entryKey }: { kind: AdminPromptKind; entryKey: string }) {
  const { t } = useTranslation();
  const { data, isLoading, error } = usePromptHistoryQuery({ kind, key: entryKey });

  return (
    <div className="settings-history">
      {isLoading && <p className="settings-muted">{t("settings.historyLoading")}</p>}
      <ErrorBanner error={error} fallbackKey="settings.historyError" className="settings-error" />
      {data && (
        <ul>
          {data.versions.map((version) => (
            <li key={version.version_id} className="settings-history-item">
              <div className="settings-history-meta">
                <span className="settings-badge">{t(`settings.source.${version.source}`)}</span>
                <span>{formatDateTime(version.created_at)}</span>
                <span>{version.created_by ?? t("settings.system")}</span>
                {version.is_active && (
                  <span className="settings-badge settings-badge--active">
                    {t("settings.active")}
                  </span>
                )}
              </div>
              <p className="settings-history-text">{version.text}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** A textarea whose height follows its text; the CSS max-height takes over
 *  for long prompts. Lives in its own component so the fit runs when the
 *  accordion opens, not only when the text changes. */
function AutoSizeTextarea({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useLayoutEffect(() => {
    const box = ref.current;
    if (box) {
      box.style.height = "auto";
      box.style.height = `${box.scrollHeight + 2}px`;
    }
  }, [value]);

  return (
    <textarea
      ref={ref}
      className="settings-textarea"
      rows={1}
      aria-label={label}
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

/** Keyed by `version_id` by its parent, so a new active version (after a
 *  save or reset) remounts it and replaces the draft. */
function PromptEntry({ version }: { version: AdminPromptVersion }) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState(version.text);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [save, saveState] = useSavePromptTextMutation();
  const [reset, resetState] = useResetPromptsMutation();
  const [remove, removeState] = useRemovePromptOptionMutation();

  const unchanged = draft.trim() === version.text;
  const busy = saveState.isLoading || resetState.isLoading || removeState.isLoading;
  const [category, optionId] = version.key.split("/");

  const confirmRemove = () => {
    if (window.confirm(t("settings.removeConfirm", { key: version.key }))) {
      void remove({ category, option_id: optionId });
    }
  };

  return (
    <Accordion
      title={version.key}
      badges={
        <>
          {version.is_default && <span className="settings-badge">{t("settings.defaultOption")}</span>}
          {version.is_custom && <span className="settings-badge">{t("settings.custom")}</span>}
          {version.is_modified && (
            <span className="settings-badge settings-badge--modified">{t("settings.modified")}</span>
          )}
        </>
      }
    >
      {version.task_ids.length > 0 && (
        <p className="settings-muted">
          {t("settings.appliesTo", { tasks: version.task_ids.join(", ") })}
        </p>
      )}
      <AutoSizeTextarea label={version.key} value={draft} onChange={setDraft} />
      <ErrorBanner error={saveState.error} fallbackKey="settings.saveError" className="settings-error" />
      <ErrorBanner error={resetState.error} fallbackKey="settings.resetError" className="settings-error" />
      <ErrorBanner error={removeState.error} fallbackKey="settings.removeError" className="settings-error" />
      <div className="settings-entry-actions">
        <Button
          disabled={unchanged || draft.trim() === "" || busy}
          onClick={() => save({ kind: version.kind, key: version.key, text: draft })}
        >
          {t("settings.save")}
        </Button>
        {version.is_custom ? (
          <Button variant="ghost" disabled={busy} onClick={confirmRemove}>
            {t("settings.remove")}
          </Button>
        ) : (
          <Button
            variant="ghost"
            disabled={!version.is_modified || busy}
            onClick={() => reset({ kind: version.kind, key: version.key })}
          >
            {t("settings.reset")}
          </Button>
        )}
        <Button variant="ghost" onClick={() => setHistoryOpen((open) => !open)}>
          {historyOpen ? t("settings.hideHistory") : t("settings.history")}
        </Button>
      </div>
      {historyOpen && <PromptHistory kind={version.kind} entryKey={version.key} />}
    </Accordion>
  );
}

/** The option categories shown together under one sub-tab. A category that
 *  is in none of them (a new one) lands under `OTHER_GROUP`. */
const OPTION_TABS: { id: string; categories: string[] }[] = [
  { id: "genre", categories: ["genre"] },
  { id: "voice", categories: ["tone", "prose_style", "perspective"] },
  {
    id: "feel",
    categories: ["pacing", "length", "player_agency", "control_mode", "consequence", "challenge"],
  },
  { id: "other", categories: [] },
];
const OTHER_GROUP = "other";

/** Categories that accept new options (the backend enforces the same list). */
const EXTENSIBLE_CATEGORIES = ["genre", "tone", "prose_style"];

/** Option keys look like `tone/balanced`; the part before the slash is the
 *  category they belong to. */
function categoryOf(entry: AdminPromptVersion): string {
  return entry.key.includes("/") ? entry.key.split("/")[0] : "";
}

function optionTabOf(category: string): string {
  return OPTION_TABS.find((tab) => tab.categories.includes(category))?.id ?? OTHER_GROUP;
}

/** The entries of one kind; options get a sub-tab per group of categories,
 *  with each category under its own heading. */
function PromptGroups({ kind, entries }: { kind: AdminPromptKind; entries: AdminPromptVersion[] }) {
  const { t } = useTranslation();
  const [selected, setSelected] = useState<string | null>(null);
  const [adding, setAdding] = useState<string | null>(null);

  if (kind !== "option") {
    return (
      <div className="settings-group">
        {entries.map((entry) => (
          <PromptEntry version={entry} key={entry.version_id} />
        ))}
      </div>
    );
  }

  const byTab = new Map<string, Map<string, AdminPromptVersion[]>>();
  for (const entry of entries) {
    const category = categoryOf(entry);
    const tab = optionTabOf(category);
    const categories = byTab.get(tab) ?? new Map<string, AdminPromptVersion[]>();
    categories.set(category, [...(categories.get(category) ?? []), entry]);
    byTab.set(tab, categories);
  }
  const ids = OPTION_TABS.map(({ id }) => id).filter((id) => byTab.has(id));
  if (ids.length === 0) {
    return null;
  }
  const activeId = selected !== null && ids.includes(selected) ? selected : ids[0];

  return (
    <Tabs
      idPrefix="group"
      tabs={ids.map((id) => ({ id, label: t(`settings.optionTab.${id}`) }))}
      activeId={activeId}
      onChange={setSelected}
    >
      {[...(byTab.get(activeId) ?? [])].map(([category, grouped]) => (
        <div className="settings-group" key={category}>
          {category && (
            <div className="settings-group-head">
              <h3>
                {t(`settings.optionGroup.${category}`, { defaultValue: formatOptionLabel(category) })}
              </h3>
              {EXTENSIBLE_CATEGORIES.includes(category) && adding !== category && (
                <Button variant="ghost" icon={<PlusIcon />} onClick={() => setAdding(category)}>
                  {t("settings.newOption.add")}
                </Button>
              )}
            </div>
          )}
          {adding === category && <NewOptionForm category={category} onClose={() => setAdding(null)} />}
          {grouped.map((entry) => (
            <PromptEntry version={entry} key={entry.version_id} />
          ))}
        </div>
      ))}
    </Tabs>
  );
}

/** The prompts of one kind, each collapsed into an accordion. */
function PromptTab({ kind }: { kind: AdminPromptKind }) {
  const { t } = useTranslation();
  const { data, isLoading, error } = useListAdminPromptsQuery();
  const [reset, resetState] = useResetPromptsMutation();
  const entries = data?.entries.filter((entry) => entry.kind === kind) ?? [];

  return (
    <section className="settings-section">
      <div className="settings-section-head">
        <h2>{t(`settings.kind.${kind}`)}</h2>
        <Button variant="ghost" disabled={resetState.isLoading} onClick={() => reset({ kind })}>
          {t("settings.resetKind", { kind: t(`settings.kind.${kind}`) })}
        </Button>
      </div>
      <p className="settings-muted">{t("settings.intro")}</p>

      {isLoading && <p className="settings-muted">{t("settings.loading")}</p>}
      <ErrorBanner error={error} fallbackKey="settings.loadError" className="settings-error" />
      <ErrorBanner error={resetState.error} fallbackKey="settings.resetError" className="settings-error" />

      <PromptGroups kind={kind} entries={entries} />
    </section>
  );
}

type SettingsTab = "models" | AdminPromptKind;

const TAB_ORDER: SettingsTab[] = ["models", "task", "option", "directive"];

/**
 * Admin-only settings (reached through `RequireAdmin`), split into tabs:
 * the model per task, then the prompts by kind. The prompts start as the
 * shipped TOML defaults; every edit is stored as a new version, so the
 * history of each entry stays traceable and a reset just appends the
 * original again. Entries are collapsed until opened.
 */
export function Settings() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<SettingsTab>("models");

  return (
    <div className="settings">
      <div className="settings-head">
        <h1>{t("settings.heading")}</h1>
      </div>

      <Tabs
        tabs={TAB_ORDER.map((id) => ({ id, label: t(`settings.tab.${id}`) }))}
        activeId={tab}
        onChange={(id) => setTab(id as SettingsTab)}
      >
        {tab === "models" ? <ModelSettings /> : <PromptTab kind={tab} />}
      </Tabs>
    </div>
  );
}
