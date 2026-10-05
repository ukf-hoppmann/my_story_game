import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  usePromptHistoryQuery,
  useListAdminPromptsQuery,
  useResetPromptsMutation,
  useSavePromptTextMutation,
} from "../../api/apiSlice";
import type { AdminPromptKind, AdminPromptVersion } from "../../api/types";
import { Button } from "../../components/Button/Button";
import { ErrorBanner } from "../../components/ErrorBanner/ErrorBanner";
import "./Settings.css";

const KIND_ORDER: AdminPromptKind[] = ["task", "option", "directive"];

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

/** Keyed by `version_id` by its parent, so a new active version (after a
 *  save or reset) remounts it and replaces the draft. */
function PromptEntry({ version }: { version: AdminPromptVersion }) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState(version.text);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [save, saveState] = useSavePromptTextMutation();
  const [reset, resetState] = useResetPromptsMutation();

  const unchanged = draft.trim() === version.text;
  const busy = saveState.isLoading || resetState.isLoading;

  return (
    <article className="settings-entry" aria-label={version.key}>
      <div className="settings-entry-head">
        <h4>{version.key}</h4>
        {version.is_default && <span className="settings-badge">{t("settings.defaultOption")}</span>}
        {version.is_modified && (
          <span className="settings-badge settings-badge--modified">{t("settings.modified")}</span>
        )}
      </div>
      {version.task_ids.length > 0 && (
        <p className="settings-muted">
          {t("settings.appliesTo", { tasks: version.task_ids.join(", ") })}
        </p>
      )}
      <textarea
        aria-label={version.key}
        value={draft}
        rows={Math.min(24, Math.max(3, draft.split("\n").length + 1))}
        onChange={(event) => setDraft(event.target.value)}
      />
      <ErrorBanner error={saveState.error} fallbackKey="settings.saveError" className="settings-error" />
      <ErrorBanner error={resetState.error} fallbackKey="settings.resetError" className="settings-error" />
      <div className="settings-entry-actions">
        <Button
          disabled={unchanged || draft.trim() === "" || busy}
          onClick={() => save({ kind: version.kind, key: version.key, text: draft })}
        >
          {t("settings.save")}
        </Button>
        <Button
          variant="ghost"
          disabled={!version.is_modified || busy}
          onClick={() => reset({ kind: version.kind, key: version.key })}
        >
          {t("settings.reset")}
        </Button>
        <Button variant="ghost" onClick={() => setHistoryOpen((open) => !open)}>
          {historyOpen ? t("settings.hideHistory") : t("settings.history")}
        </Button>
      </div>
      {historyOpen && <PromptHistory kind={version.kind} entryKey={version.key} />}
    </article>
  );
}

/**
 * Admin-only settings (reached through `RequireAdmin`). The prompts start as
 * the shipped TOML defaults; every edit is stored as a new version, so the
 * history of each entry stays traceable and a reset just appends the
 * original again.
 */
export function Settings() {
  const { t } = useTranslation();
  const { data, isLoading, error } = useListAdminPromptsQuery();
  const [reset, resetState] = useResetPromptsMutation();

  return (
    <div className="settings">
      <div className="settings-head">
        <h1>{t("settings.heading")}</h1>
      </div>

      <section>
        <div className="settings-section-head">
          <h2>{t("settings.promptsHeading")}</h2>
          <Button variant="ghost" disabled={resetState.isLoading} onClick={() => reset({})}>
            {t("settings.resetAll")}
          </Button>
        </div>
        <p className="settings-muted">{t("settings.intro")}</p>

        {isLoading && <p className="settings-muted">{t("settings.loading")}</p>}
        <ErrorBanner error={error} fallbackKey="settings.loadError" className="settings-error" />
        <ErrorBanner error={resetState.error} fallbackKey="settings.resetError" className="settings-error" />

        {data &&
          KIND_ORDER.map((kind) => {
            const entries = data.entries.filter((entry) => entry.kind === kind);
            if (entries.length === 0) {
              return null;
            }
            return (
              <div className="settings-group" key={kind}>
                <h3>{t(`settings.kind.${kind}`)}</h3>
                {entries.map((entry) => (
                  <PromptEntry version={entry} key={entry.version_id} />
                ))}
              </div>
            );
          })}
      </section>
    </div>
  );
}
