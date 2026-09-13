import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useListRunsQuery } from "../../api/apiSlice";
import type { GameRunStatus, RunSummary } from "../../api/types";
import { ArrowRightIcon } from "../../icons";
import { Button } from "../../components/Button/Button";
import { ErrorBanner } from "../../components/ErrorBanner/ErrorBanner";
import "./Library.css";

const STATUS_LABEL_KEYS: Record<GameRunStatus, string> = {
  draft: "library.status.draft",
  active: "library.status.active",
  paused: "library.status.paused",
  completed: "library.status.completed",
};

function formatUpdatedAt(iso: string): string {
  return new Date(iso).toLocaleDateString("de-DE", { day: "2-digit", month: "short" });
}

function RunCard({ run }: { run: RunSummary }) {
  const navigate = useNavigate();
  const { t } = useTranslation();

  return (
    <button
      type="button"
      className="run-card"
      onClick={() => navigate(`/stories/${run.id}`)}
    >
      <div className="run-card-title">{run.name}</div>
      <div className="run-card-meta">
        <span className={`run-status${run.status === "active" ? " run-status--active" : ""}`}>
          {t(STATUS_LABEL_KEYS[run.status])}
        </span>
        <span className="run-updated">{formatUpdatedAt(run.updated_at)}</span>
      </div>
    </button>
  );
}

export function Library() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { data: runs, isLoading, error } = useListRunsQuery();

  const drafts = runs?.filter((run) => run.status === "draft") ?? [];
  const active = runs?.filter((run) => run.status !== "draft") ?? [];

  return (
    <div className="library">
      <div className="library-head">
        <h1>{t("library.heading")}</h1>
        <Button icon={<ArrowRightIcon />} onClick={() => navigate("/new")}>
          {t("library.newStory")}
        </Button>
      </div>

      {isLoading && <p className="library-empty">{t("library.loading")}</p>}

      <ErrorBanner error={error} fallbackKey="library.loadError" className="library-error" />

      {runs && (
        <>
          <section className="library-group">
            <div className="library-group-label">{t("library.activeGroupLabel")}</div>
            {active.length === 0 ? (
              <p className="library-empty">{t("library.noActiveStories")}</p>
            ) : (
              <div className="library-grid">
                {active.map((run) => (
                  <RunCard run={run} key={run.id} />
                ))}
              </div>
            )}
          </section>

          <section className="library-group">
            <div className="library-group-label">{t("library.draftsGroupLabel")}</div>
            {drafts.length === 0 ? (
              <p className="library-empty">{t("library.noDrafts")}</p>
            ) : (
              <div className="library-grid">
                {drafts.map((run) => (
                  <RunCard run={run} key={run.id} />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
