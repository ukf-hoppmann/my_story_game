import { useTranslation } from "react-i18next";
import { useSaveWorldTrackingMutation, useWorldTrackingQuery } from "../../api/apiSlice";
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

/**
 * Global game switches. World tracking can be turned off for weak local
 * models: then no world extraction runs, at story start or on any turn,
 * and the change applies from the next turn, also in running games.
 */
export function GameSettings() {
  const { t } = useTranslation();
  const { data, isLoading, error } = useWorldTrackingQuery();
  const [save, saveState] = useSaveWorldTrackingMutation();

  return (
    <section className="settings-section">
      <div className="settings-section-head">
        <h2>{t("settings.gameHeading")}</h2>
      </div>
      {isLoading && <p className="settings-muted">{t("settings.worldTracking.loading")}</p>}
      <ErrorBanner error={error} fallbackKey="settings.worldTracking.loadError" className="settings-error" />
      {data && (
        <div className="settings-group">
          <label className="settings-toggle">
            <input
              type="checkbox"
              checked={data.enabled}
              disabled={saveState.isLoading}
              onChange={(event) => save(event.target.checked)}
            />
            <span>{t("settings.worldTracking.label")}</span>
          </label>
          <p className="settings-muted">{t("settings.worldTracking.hint")}</p>
          {data.updated_at && (
            <p className="settings-muted">
              {t("settings.worldTracking.changed", {
                at: formatDateTime(data.updated_at),
                by: data.updated_by ?? t("settings.system"),
              })}
            </p>
          )}
          <ErrorBanner
            error={saveState.error}
            fallbackKey="settings.saveError"
            className="settings-error"
          />
        </div>
      )}
    </section>
  );
}
