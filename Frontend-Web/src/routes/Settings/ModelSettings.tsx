import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  useListAdminModelsQuery,
  useModelHistoryQuery,
  useResetModelSettingsMutation,
  useSaveModelSettingMutation,
} from "../../api/apiSlice";
import type {
  AdminModelCandidate,
  AdminModelSetting,
  AdminModelTask,
} from "../../api/types";
import { Accordion } from "../../components/Accordion/Accordion";
import { Button } from "../../components/Button/Button";
import { ErrorBanner } from "../../components/ErrorBanner/ErrorBanner";

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function describeOptions(setting: AdminModelSetting): string {
  const parts: string[] = [];
  if (setting.temperature !== null) {
    parts.push(`T ${setting.temperature}`);
  }
  if (setting.max_output_tokens !== null) {
    parts.push(`≤ ${setting.max_output_tokens}`);
  }
  return parts.join(", ");
}

function ModelHistory({ task }: { task: AdminModelTask }) {
  const { t } = useTranslation();
  const { data, isLoading, error } = useModelHistoryQuery(task);

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
              <p className="settings-history-text">
                {version.model_ref}
                {describeOptions(version) && ` (${describeOptions(version)})`}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function parseNumber(raw: string): number | null {
  const trimmed = raw.trim();
  return trimmed === "" ? null : Number(trimmed);
}

/** Keyed by `version_id` by its parent, so a new active version (after a save
 *  or reset) remounts it and replaces the draft. */
function ModelCard({
  version,
  candidates,
}: {
  version: AdminModelSetting;
  candidates: AdminModelCandidate[];
}) {
  const { t } = useTranslation();
  const [modelRef, setModelRef] = useState(version.model_ref);
  const [temperature, setTemperature] = useState(
    version.temperature === null ? "" : String(version.temperature),
  );
  const [maxTokens, setMaxTokens] = useState(
    version.max_output_tokens === null ? "" : String(version.max_output_tokens),
  );
  const [historyOpen, setHistoryOpen] = useState(false);
  const [save, saveState] = useSaveModelSettingMutation();
  const [reset, resetState] = useResetModelSettingsMutation();

  const draftTemperature = parseNumber(temperature);
  const draftMaxTokens = parseNumber(maxTokens);
  const unchanged =
    modelRef === version.model_ref &&
    draftTemperature === version.temperature &&
    draftMaxTokens === version.max_output_tokens;
  const invalid = Number.isNaN(draftTemperature) || Number.isNaN(draftMaxTokens);
  const busy = saveState.isLoading || resetState.isLoading;
  const label = t(`settings.task.${version.task}`);

  return (
    <Accordion
      title={label}
      badges={
        version.is_modified && (
          <span className="settings-badge settings-badge--modified">{t("settings.modified")}</span>
        )
      }
      summary={`${version.model_ref}${describeOptions(version) && ` (${describeOptions(version)})`}`}
    >
      <div className="settings-fields">
        <label className="settings-field">
          <span>{t("settings.model")}</span>
          <select value={modelRef} onChange={(event) => setModelRef(event.target.value)}>
            {candidates.map((candidate) => (
              <option key={candidate.model_ref} value={candidate.model_ref}>
                {candidate.provider_id} · {candidate.model_id}
              </option>
            ))}
          </select>
        </label>
        <label className="settings-field">
          <span>{t("settings.temperature")}</span>
          <input
            type="number"
            step="0.1"
            min="0"
            max="2"
            value={temperature}
            onChange={(event) => setTemperature(event.target.value)}
          />
        </label>
        <label className="settings-field">
          <span>{t("settings.maxOutputTokens")}</span>
          <input
            type="number"
            step="1"
            min="1"
            value={maxTokens}
            onChange={(event) => setMaxTokens(event.target.value)}
          />
        </label>
      </div>
      <p className="settings-muted">{t("settings.defaultHint")}</p>
      <ErrorBanner error={saveState.error} fallbackKey="settings.saveError" className="settings-error" />
      <ErrorBanner error={resetState.error} fallbackKey="settings.resetError" className="settings-error" />
      <div className="settings-entry-actions">
        <Button
          disabled={unchanged || invalid || busy}
          onClick={() =>
            save({
              task: version.task,
              model_ref: modelRef,
              temperature: draftTemperature,
              max_output_tokens: draftMaxTokens,
            })
          }
        >
          {t("settings.save")}
        </Button>
        <Button
          variant="ghost"
          disabled={!version.is_modified || busy}
          onClick={() => reset({ task: version.task })}
        >
          {t("settings.reset")}
        </Button>
        <Button variant="ghost" onClick={() => setHistoryOpen((open) => !open)}>
          {historyOpen ? t("settings.hideHistory") : t("settings.history")}
        </Button>
      </div>
      {historyOpen && <ModelHistory task={version.task} />}
    </Accordion>
  );
}

/**
 * Which catalog model each task uses, with its generation options. Every
 * edit is stored as a new version, like the prompts; a reset appends the
 * value from the configuration file again.
 */
export function ModelSettings() {
  const { t } = useTranslation();
  const { data, isLoading, error } = useListAdminModelsQuery();
  const [reset, resetState] = useResetModelSettingsMutation();

  return (
    <section className="settings-section">
      <div className="settings-section-head">
        <h2>{t("settings.modelsHeading")}</h2>
        <Button variant="ghost" disabled={resetState.isLoading} onClick={() => reset({})}>
          {t("settings.resetAllModels")}
        </Button>
      </div>
      <p className="settings-muted">{t("settings.modelsIntro")}</p>

      {isLoading && <p className="settings-muted">{t("settings.modelsLoading")}</p>}
      <ErrorBanner error={error} fallbackKey="settings.modelsLoadError" className="settings-error" />
      <ErrorBanner error={resetState.error} fallbackKey="settings.resetError" className="settings-error" />

      {data && (
        <div className="settings-group">
          {data.settings.map((version) => (
            <ModelCard
              version={version}
              candidates={data.candidates.filter((c) => c.task === version.task)}
              key={version.version_id}
            />
          ))}
        </div>
      )}
    </section>
  );
}
