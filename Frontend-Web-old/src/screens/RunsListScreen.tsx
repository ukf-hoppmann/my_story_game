import { useEffect } from "react";
import { listRuns } from "../api/client";
import { errorMessage, useApiRequest } from "../api/useApiRequest";
import type { RunSummary } from "../api/types";

interface Props {
  onSelectDraft: (run: RunSummary) => void;
  onSelectActive: (run: RunSummary) => void;
  onStartNew: () => void;
}

function RunCard({ item, onClick }: { item: RunSummary; onClick: () => void }) {
  return (
    <div className="card" style={{ cursor: "pointer" }} onClick={onClick}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <strong>{item.name}</strong>
        <span className="badge">{item.status}</span>
      </div>
      <p style={{ margin: "6px 0 0", fontSize: "0.85rem", color: "var(--ink-dim)" }}>
        Revision {item.current_revision} · zuletzt aktualisiert{" "}
        {new Date(item.updated_at).toLocaleString("de-DE")}
      </p>
    </div>
  );
}

export function RunsListScreen({ onSelectDraft, onSelectActive, onStartNew }: Props) {
  const [state, run] = useApiRequest(listRuns);

  useEffect(() => {
    void run();
  }, [run]);

  const drafts =
    state.status === "success" ? state.data.runs.filter((item) => item.status === "draft") : [];
  const active =
    state.status === "success" ? state.data.runs.filter((item) => item.status !== "draft") : [];

  return (
    <div>
      <h1>Deine Geschichten</h1>
      <button className="primary" onClick={onStartNew} style={{ marginBottom: 20 }}>
        Neue Geschichte beginnen
      </button>

      {state.status === "loading" && <p>Lädt…</p>}
      {state.status === "error" && (
        <div className="error-banner">{errorMessage(state.error)}</div>
      )}

      {state.status === "success" && (
        <>
          <h2>Laufende Spiele</h2>
          {active.length === 0 && (
            <p style={{ color: "var(--ink-dim)" }}>Noch kein Spiel gestartet.</p>
          )}
          {active.map((item) => (
            <RunCard key={item.id} item={item} onClick={() => onSelectActive(item)} />
          ))}

          <h2 style={{ marginTop: 28 }}>Vorlagen</h2>
          {drafts.length === 0 && (
            <p style={{ color: "var(--ink-dim)" }}>
              Noch keine Vorlagen. Beginne eine neue Geschichte.
            </p>
          )}
          {drafts.map((item) => (
            <RunCard key={item.id} item={item} onClick={() => onSelectDraft(item)} />
          ))}
        </>
      )}
    </div>
  );
}
