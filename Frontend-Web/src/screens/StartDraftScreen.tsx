import { useState } from "react";
import { createDraft, startPlaythrough } from "../api/client";
import { errorMessage, useApiRequest } from "../api/useApiRequest";
import type { ControlMode } from "../api/types";

interface Props {
  onBack: () => void;
  onPlaythroughStarted: (runId: string) => void;
}

export function StartDraftScreen({ onBack, onPlaythroughStarted }: Props) {
  const [runName, setRunName] = useState("");
  const [initialPrompt, setInitialPrompt] = useState("");
  const [controlMode, setControlMode] = useState<ControlMode>("player");
  const [characterName, setCharacterName] = useState("");
  const [characterDescription, setCharacterDescription] = useState("");

  const [createState, runCreate] = useApiRequest(createDraft);
  const [playthroughState, runPlaythrough] = useApiRequest(startPlaythrough);

  const busy = createState.status === "loading" || playthroughState.status === "loading";

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const draft = await runCreate({
      run_name: runName,
      initial_prompt: initialPrompt,
      control_mode: controlMode,
      controllable_characters:
        controlMode === "player"
          ? [{ name: characterName, description: characterDescription }]
          : [],
    });
    if (!draft) return;

    const active = await runPlaythrough(draft.game_run.id);
    if (!active) return;

    onPlaythroughStarted(active.game_run.id);
  }

  return (
    <div>
      <button onClick={onBack} style={{ marginBottom: 16 }}>
        ← Zurück
      </button>
      <h1>Neue Geschichte beginnen</h1>

      {createState.status === "error" && (
        <div className="error-banner">{errorMessage(createState.error)}</div>
      )}
      {playthroughState.status === "error" && (
        <div className="error-banner">{errorMessage(playthroughState.error)}</div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="run_name">Titel</label>
          <input
            id="run_name"
            required
            value={runName}
            onChange={(event) => setRunName(event.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="initial_prompt">Womit beginnt deine Geschichte?</label>
          <textarea
            id="initial_prompt"
            rows={3}
            required
            value={initialPrompt}
            onChange={(event) => setInitialPrompt(event.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="control_mode">Modus</label>
          <select
            id="control_mode"
            value={controlMode}
            onChange={(event) => setControlMode(event.target.value as ControlMode)}
          >
            <option value="player">Spieler-Modus</option>
            <option value="director">Regie-Modus</option>
          </select>
        </div>

        {controlMode === "player" && (
          <>
            <div className="field">
              <label htmlFor="character_name">Name deiner Figur</label>
              <input
                id="character_name"
                required
                value={characterName}
                onChange={(event) => setCharacterName(event.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="character_description">Kurzbeschreibung</label>
              <input
                id="character_description"
                value={characterDescription}
                onChange={(event) => setCharacterDescription(event.target.value)}
              />
            </div>
          </>
        )}

        <button className="primary" type="submit" disabled={busy}>
          {busy ? "Wird erzeugt…" : "Geschichte beginnen"}
        </button>
      </form>
    </div>
  );
}
