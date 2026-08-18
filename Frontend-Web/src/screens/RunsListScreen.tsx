import { useEffect } from "react";
import { listRuns } from "../api/client";
import { errorMessage, useApiRequest } from "../api/useApiRequest";
import type { RunSummary } from "../api/types";

interface Props {
  onSelectDraft: (run: RunSummary) => void;
  onSelectActive: (run: RunSummary) => void;
  onStartNew: () => void;
}

export function RunsListScreen({ onSelectDraft, onSelectActive, onStartNew }: Props) {
  const [state, run] = useApiRequest(listRuns);

  useEffect(() => {
    void run();
  }, [run]);

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
      {state.status === "success" && state.data.runs.length === 0 && (
        <p>Noch keine Geschichten. Beginne eine neue.</p>
      )}
      {state.status === "success" &&
        state.data.runs.map((item) => (
          <div
            key={item.id}
            className="card"
            style={{ cursor: "pointer" }}
            onClick={() => (item.status === "draft" ? onSelectDraft(item) : onSelectActive(item))}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong>{item.name}</strong>
              <span className="badge">{item.status}</span>
            </div>
            <p style={{ margin: "6px 0 0", fontSize: "0.85rem", color: "var(--ink-dim)" }}>
              Revision {item.current_revision} · zuletzt aktualisiert{" "}
              {new Date(item.updated_at).toLocaleString("de-DE")}
            </p>
          </div>
        ))}
    </div>
  );
}
