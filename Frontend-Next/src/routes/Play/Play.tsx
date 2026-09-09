import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useLoadRunQuery, usePlayTurnMutation, useStartPlaythroughMutation } from "../../api/apiSlice";
import { Paragraphs } from "../../components/Paragraphs";
import { Button } from "../../components/Button/Button";
import {
  ArrowRightIcon,
  BookIcon,
  CompassIcon,
  GlobeIcon,
  ScrollIcon,
  TargetIcon,
} from "../../icons";
import "./Play.css";

/** Recovery copy for the error codes the old PlayScreen specifically
 *  handled — a stale run or a concurrent-edit conflict both need a reload,
 *  not just "something went wrong". */
const TURN_ERROR_MESSAGES: Record<string, string> = {
  run_not_active: "Diese Geschichte läuft nicht mehr. Lade sie neu, um den aktuellen Stand zu sehen.",
  revision_conflict: "Es gab zwischenzeitlich eine neue Aktualisierung. Lade die Geschichte neu.",
};

/** RTK Query's error union also includes plain `SerializedError` (thrown JS
 *  errors), which has no guaranteed `code` — narrow defensively instead of
 *  assuming our own QueryError shape. */
function errorCode(error: unknown): string | undefined {
  if (error && typeof error === "object" && "code" in error && typeof error.code === "string") {
    return error.code;
  }
  return undefined;
}

export function Play() {
  const { runId = "" } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [input, setInput] = useState("");

  const { data: doc, isLoading, error, refetch } = useLoadRunQuery(runId, { skip: runId === "" });
  const [playTurn, playTurnState] = usePlayTurnMutation();
  const [startPlaythrough, startState] = useStartPlaythroughMutation();

  async function handleSubmitTurn() {
    if (input.trim().length === 0) {
      return;
    }
    const result = await playTurn({ runId, payload: { player_input: input } });
    if (!("error" in result)) {
      setInput("");
    }
  }

  async function handleStartPlaythrough() {
    try {
      const active = await startPlaythrough(runId).unwrap();
      navigate(`/stories/${active.game_run.id}`);
    } catch {
      // Surfaced via startState.error below.
    }
  }

  return (
    <div className="play-shell">
      <aside className="play-rail">
        <div className="play-brand">
          <CompassIcon />
          <span className="play-brand-name">{doc?.game_run.name ?? "Story Game"}</span>
        </div>

        <nav className="play-nav">
          <div className="play-nav-item play-nav-item--active">
            <BookIcon />
            Geschichte
          </div>
          <div className="play-nav-item">
            <GlobeIcon />
            Welt
          </div>
          <div className="play-nav-item">
            <TargetIcon />
            Ziele
          </div>
          <div className="play-nav-item">
            <ScrollIcon />
            Chronik
          </div>
        </nav>

        <div className="play-rail-foot">„Jede Entscheidung hinterlässt Spuren.“</div>
      </aside>

      <main className="play-stage">
        {isLoading && <p className="play-status">Lade Geschichte …</p>}

        {error && (
          <div className="play-error-banner">
            <span>Die Geschichte konnte nicht geladen werden.</span>
            <Button variant="ghost" onClick={() => refetch()}>
              Erneut versuchen
            </Button>
          </div>
        )}

        {doc && doc.game_run.status !== "active" && (
          <div className="play-draft-banner">
            <p>Diese Geschichte ist noch ein Entwurf. Starte sie, um loszulegen.</p>
            {startState.error && <p className="play-status">Das Starten hat nicht geklappt. Versuch's noch mal.</p>}
            <Button
              icon={<ArrowRightIcon />}
              disabled={startState.isLoading}
              onClick={handleStartPlaythrough}
            >
              {startState.isLoading ? "Wird gestartet …" : "Spiel starten"}
            </Button>
          </div>
        )}

        {doc && doc.game_run.status === "active" && (
          <>
            <div className="play-scene-header">
              <h1>{doc.game_run.name}</h1>
              <span className="play-turn-badge">Zug {doc.game_state.story.current_turn_sequence}</span>
            </div>

            <div className="play-story-feed">
              {doc.game_state.story.initialization && (
                <div className="play-turn">
                  <Paragraphs text={doc.game_state.story.initialization.narration} />
                </div>
              )}
              {doc.game_state.story.turns.map((turn) => (
                <div className="play-turn" key={turn.id}>
                  <p className="play-turn-input">Du: {turn.player_input}</p>
                  <Paragraphs text={turn.narration} />
                </div>
              ))}
            </div>

            {playTurnState.error && (
              <div className="play-error-banner">
                <span>
                  {(() => {
                    const code = errorCode(playTurnState.error);
                    return (code && TURN_ERROR_MESSAGES[code]) ?? "Deine Handlung konnte nicht verarbeitet werden.";
                  })()}
                </span>
                <Button variant="ghost" onClick={() => refetch()}>
                  Neu laden
                </Button>
              </div>
            )}

            <div className="play-action-row">
              <label className="play-action-input">
                <input
                  type="text"
                  placeholder="Was tust du?"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      handleSubmitTurn();
                    }
                  }}
                />
              </label>
              <Button
                icon={<ArrowRightIcon />}
                disabled={playTurnState.isLoading || input.trim().length === 0}
                onClick={handleSubmitTurn}
              >
                {playTurnState.isLoading ? "Wird ausgeführt …" : "Handlung ausführen"}
              </Button>
            </div>
          </>
        )}
      </main>

      <aside className="play-sidebar">
        <p className="play-sidebar-note">Ziele, Weltwissen und Figuren folgen in Schritt 10.</p>
      </aside>
    </div>
  );
}
