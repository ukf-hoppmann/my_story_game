import { useNavigate } from "react-router-dom";
import { useListRunsQuery } from "../../api/apiSlice";
import type { GameRunStatus, RunSummary } from "../../api/types";
import { ArrowRightIcon } from "../../icons";
import { Button } from "../../components/Button/Button";
import "./Library.css";

const STATUS_LABELS: Record<GameRunStatus, string> = {
  draft: "Entwurf",
  active: "Aktiv",
  paused: "Pausiert",
  completed: "Abgeschlossen",
};

function formatUpdatedAt(iso: string): string {
  return new Date(iso).toLocaleDateString("de-DE", { day: "2-digit", month: "short" });
}

function RunCard({ run }: { run: RunSummary }) {
  const navigate = useNavigate();

  return (
    <button
      type="button"
      className="run-card"
      onClick={() => navigate(`/stories/${run.id}`)}
    >
      <div className="run-card-title">{run.name}</div>
      <div className="run-card-meta">
        <span className={`run-status${run.status === "active" ? " run-status--active" : ""}`}>
          {STATUS_LABELS[run.status]}
        </span>
        <span className="run-updated">{formatUpdatedAt(run.updated_at)}</span>
      </div>
    </button>
  );
}

export function Library() {
  const navigate = useNavigate();
  const { data: runs, isLoading, error } = useListRunsQuery();

  const drafts = runs?.filter((run) => run.status === "draft") ?? [];
  const active = runs?.filter((run) => run.status !== "draft") ?? [];

  return (
    <div className="library">
      <div className="library-head">
        <h1>Deine Geschichten</h1>
        <Button icon={<ArrowRightIcon />} onClick={() => navigate("/new")}>
          Neue Geschichte
        </Button>
      </div>

      {isLoading && <p className="library-empty">Lade deine Geschichten …</p>}

      {error && (
        <p className="library-error">
          Deine Geschichten konnten nicht geladen werden. Bitte versuche es erneut.
        </p>
      )}

      {runs && (
        <>
          <section className="library-group">
            <div className="library-group-label">Aktive Geschichten</div>
            {active.length === 0 ? (
              <p className="library-empty">Noch keine aktive Geschichte — leg los!</p>
            ) : (
              <div className="library-grid">
                {active.map((run) => (
                  <RunCard run={run} key={run.id} />
                ))}
              </div>
            )}
          </section>

          <section className="library-group">
            <div className="library-group-label">Entwürfe</div>
            {drafts.length === 0 ? (
              <p className="library-empty">Keine offenen Entwürfe.</p>
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
