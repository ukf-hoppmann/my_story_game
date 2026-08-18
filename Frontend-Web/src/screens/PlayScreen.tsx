import { useEffect, useState } from "react";
import { loadRun, playTurn, startPlaythrough } from "../api/client";
import { ApiError } from "../api/client";
import { errorMessage, useApiRequest } from "../api/useApiRequest";
import type { GameDocument } from "../api/types";

interface Props {
  runId: string;
  onBack: () => void;
}

export function PlayScreen({ runId, onBack }: Props) {
  const [currentRunId, setCurrentRunId] = useState(runId);
  const [doc, setDoc] = useState<GameDocument | null>(null);
  const [playerInput, setPlayerInput] = useState("");

  const [loadState, runLoad] = useApiRequest(loadRun);
  const [playthroughState, runPlaythrough] = useApiRequest(startPlaythrough);
  const [turnState, runTurn] = useApiRequest(playTurn);

  useEffect(() => {
    void runLoad(currentRunId).then((loaded) => {
      if (loaded) setDoc(loaded);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentRunId]);

  async function handleStartPlaythrough() {
    const active = await runPlaythrough(currentRunId);
    if (!active) return;
    setDoc(active);
    setCurrentRunId(active.game_run.id);
  }

  async function handleSubmitTurn(event: React.FormEvent) {
    event.preventDefault();
    if (!playerInput.trim()) return;
    const result = await runTurn(currentRunId, { player_input: playerInput });
    if (!result) return;
    setDoc((previous) => (previous ? { ...previous, game_state: result.state } : previous));
    setPlayerInput("");
  }

  const turnError =
    turnState.status === "error" && turnState.error instanceof ApiError
      ? turnState.error
      : null;
  const needsReload = turnError?.code === "run_not_active" || turnError?.code === "revision_conflict";

  return (
    <div>
      <button onClick={onBack} style={{ marginBottom: 16 }}>
        ← Zurück zur Liste
      </button>

      {loadState.status === "loading" && <p>Lädt…</p>}
      {loadState.status === "error" && (
        <div className="error-banner">{errorMessage(loadState.error)}</div>
      )}

      {doc && (
        <>
          <h1>{doc.game_run.name}</h1>
          <p style={{ color: "var(--ink-dim)" }}>
            Status <span className="badge">{doc.game_run.status}</span> · Revision{" "}
            {doc.game_state.revision}
          </p>

          {doc.game_run.status !== "active" ? (
            <div className="card">
              <p>Diese Geschichte ist noch eine Vorlage und wurde noch nicht gestartet.</p>
              {playthroughState.status === "error" && (
                <div className="error-banner">{errorMessage(playthroughState.error)}</div>
              )}
              <button
                className="primary"
                onClick={handleStartPlaythrough}
                disabled={playthroughState.status === "loading"}
              >
                {playthroughState.status === "loading" ? "Wird gestartet…" : "Spiel starten"}
              </button>
            </div>
          ) : (
            <>
              <section>
                {doc.game_state.story.turns.map((turn) => (
                  <div key={turn.id} style={{ marginBottom: 18 }}>
                    <p style={{ fontSize: "0.8rem", color: "var(--ink-dim)" }}>
                      Zug {turn.sequence}
                    </p>
                    <p style={{ fontStyle: "italic", color: "var(--accent)" }}>
                      {turn.player_input}
                    </p>
                    <p>{turn.narration}</p>
                  </div>
                ))}
              </section>

              {turnState.status === "error" && (
                <div className="error-banner">
                  {errorMessage(turnState.error)}
                  {needsReload && (
                    <>
                      {" "}
                      <button onClick={() => void runLoad(currentRunId).then((d) => d && setDoc(d))}>
                        Neu laden
                      </button>
                    </>
                  )}
                </div>
              )}
              {turnState.status === "success" && turnState.data.summary_failed && (
                <div className="error-banner">
                  Die Zusammenfassung konnte nicht erzeugt werden
                  {turnState.data.summary_failure_message
                    ? `: ${turnState.data.summary_failure_message}`
                    : "."}{" "}
                  Der Zug selbst wurde trotzdem gespeichert.
                </div>
              )}

              <form onSubmit={handleSubmitTurn}>
                <div className="field">
                  <textarea
                    rows={2}
                    placeholder="Was tust du als Nächstes?"
                    value={playerInput}
                    disabled={turnState.status === "loading"}
                    onChange={(event) => setPlayerInput(event.target.value)}
                  />
                </div>
                <button className="primary" type="submit" disabled={turnState.status === "loading"}>
                  {turnState.status === "loading" ? "Der Zug wird verarbeitet…" : "Zug senden"}
                </button>
              </form>
            </>
          )}
        </>
      )}
    </div>
  );
}
