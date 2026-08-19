import { useState } from "react";
import { confirmRun, proposeRun, startPlaythrough } from "../api/client";
import { errorMessage, useApiRequest } from "../api/useApiRequest";
import type {
  CharacterDecision,
  ControlMode,
  ItemDecision,
  RunProposal,
} from "../api/types";

interface Props {
  onBack: () => void;
  onPlaythroughStarted: (runId: string) => void;
}

export function StartDraftScreen({ onBack, onPlaythroughStarted }: Props) {
  const [step, setStep] = useState<"prompt" | "review">("prompt");
  const [proposal, setProposal] = useState<RunProposal | null>(null);

  const [initialPrompt, setInitialPrompt] = useState("");
  const [controlMode, setControlMode] = useState<ControlMode>("player");
  const [characterName, setCharacterName] = useState("");
  const [characterDescription, setCharacterDescription] = useState("");

  const [runName, setRunName] = useState("");
  const [characterRoles, setCharacterRoles] = useState<Record<string, "player" | "npc">>({});
  const [removedEntityIds, setRemovedEntityIds] = useState<Set<string>>(new Set());

  const [proposeState, runPropose] = useApiRequest(proposeRun);
  const [confirmState, runConfirm] = useApiRequest(confirmRun);
  const [playthroughState, runPlaythrough] = useApiRequest(startPlaythrough);

  const busy =
    proposeState.status === "loading" ||
    confirmState.status === "loading" ||
    playthroughState.status === "loading";

  async function handleSubmitPrompt(event: React.FormEvent) {
    event.preventDefault();
    const result = await runPropose({
      initial_prompt: initialPrompt,
      control_mode: controlMode,
      controllable_characters:
        controlMode === "player"
          ? [{ name: characterName, description: characterDescription }]
          : [],
    });
    if (!result) return;

    const initialRoles: Record<string, "player" | "npc"> = {};
    for (const entity of result.world.entities) {
      if (entity.kind === "character") {
        initialRoles[entity.id] = result.suggested_player_entity_ids.includes(entity.id)
          ? "player"
          : "npc";
      }
    }
    setProposal(result);
    setCharacterRoles(initialRoles);
    setRemovedEntityIds(new Set());
    setRunName(result.suggested_title);
    setStep("review");
  }

  function handleBackToPrompt() {
    setProposal(null);
    setStep("prompt");
  }

  function toggleRemoved(entityId: string) {
    setRemovedEntityIds((previous) => {
      const next = new Set(previous);
      if (next.has(entityId)) {
        next.delete(entityId);
      } else {
        next.add(entityId);
      }
      return next;
    });
  }

  async function handleSubmitReview(event: React.FormEvent) {
    event.preventDefault();
    if (!proposal) return;

    const characterDecisions: CharacterDecision[] = proposal.world.entities
      .filter((entity) => entity.kind === "character")
      .map((entity) => ({
        entity_id: entity.id,
        role: characterRoles[entity.id] ?? "npc",
        removed: removedEntityIds.has(entity.id),
      }));

    const itemDecisions: ItemDecision[] = proposal.world.entities
      .filter((entity) => entity.kind === "item")
      .map((entity) => ({
        entity_id: entity.id,
        removed: removedEntityIds.has(entity.id),
      }));

    const draft = await runConfirm({
      proposal_id: proposal.proposal_id,
      run_name: runName.trim() || undefined,
      character_decisions: characterDecisions,
      item_decisions: itemDecisions,
    });
    if (!draft) return;

    const active = await runPlaythrough(draft.game_run.id);
    if (!active) return;

    onPlaythroughStarted(active.game_run.id);
  }

  if (step === "review" && proposal) {
    const characters = proposal.world.entities.filter((entity) => entity.kind === "character");
    const items = proposal.world.entities.filter((entity) => entity.kind === "item");
    const others = proposal.world.entities.filter(
      (entity) => entity.kind !== "character" && entity.kind !== "item",
    );

    return (
      <div>
        <button onClick={handleBackToPrompt} style={{ marginBottom: 16 }}>
          ← Zurück
        </button>
        <h1>Vorschlag prüfen</h1>

        <div className="card">
          <p>{proposal.opening_narration}</p>
        </div>

        {confirmState.status === "error" && (
          <div className="error-banner">{errorMessage(confirmState.error)}</div>
        )}
        {playthroughState.status === "error" && (
          <div className="error-banner">{errorMessage(playthroughState.error)}</div>
        )}

        <form onSubmit={handleSubmitReview}>
          <div className="field">
            <label htmlFor="run_name">Titel (Vorschlag, kann angepasst werden)</label>
            <input
              id="run_name"
              value={runName}
              onChange={(event) => setRunName(event.target.value)}
            />
          </div>

          {characters.length > 0 && (
            <>
              <h2>Figuren</h2>
              {characters.map((entity) => (
                <div key={entity.id} className="card">
                  <strong>{entity.label}</strong>
                  {entity.description && (
                    <p style={{ color: "var(--ink-dim)", margin: "4px 0 8px" }}>
                      {entity.description}
                    </p>
                  )}
                  <div className="field" style={{ marginBottom: 8 }}>
                    <select
                      value={characterRoles[entity.id] ?? "npc"}
                      disabled={removedEntityIds.has(entity.id)}
                      onChange={(event) =>
                        setCharacterRoles((previous) => ({
                          ...previous,
                          [entity.id]: event.target.value as "player" | "npc",
                        }))
                      }
                    >
                      <option value="player">Spieler</option>
                      <option value="npc">NPC</option>
                    </select>
                  </div>
                  <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <input
                      type="checkbox"
                      checked={removedEntityIds.has(entity.id)}
                      onChange={() => toggleRemoved(entity.id)}
                    />
                    Verwerfen
                  </label>
                </div>
              ))}
            </>
          )}

          {items.length > 0 && (
            <>
              <h2>Gegenstände</h2>
              {items.map((entity) => (
                <div key={entity.id} className="card">
                  <strong>{entity.label}</strong>
                  {entity.description && (
                    <p style={{ color: "var(--ink-dim)", margin: "4px 0 8px" }}>
                      {entity.description}
                    </p>
                  )}
                  <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <input
                      type="checkbox"
                      checked={removedEntityIds.has(entity.id)}
                      onChange={() => toggleRemoved(entity.id)}
                    />
                    Verwerfen
                  </label>
                </div>
              ))}
            </>
          )}

          {others.length > 0 && (
            <>
              <h2>Weitere Elemente</h2>
              {others.map((entity) => (
                <div key={entity.id} className="card">
                  <strong>{entity.label}</strong> <span className="badge">{entity.kind}</span>
                  {entity.description && (
                    <p style={{ color: "var(--ink-dim)", margin: "4px 0 0" }}>
                      {entity.description}
                    </p>
                  )}
                </div>
              ))}
            </>
          )}

          <button className="primary" type="submit" disabled={busy}>
            {busy ? "Wird erzeugt…" : "Geschichte beginnen"}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div>
      <button onClick={onBack} style={{ marginBottom: 16 }}>
        ← Zurück
      </button>
      <h1>Neue Geschichte beginnen</h1>

      {proposeState.status === "error" && (
        <div className="error-banner">{errorMessage(proposeState.error)}</div>
      )}

      <form onSubmit={handleSubmitPrompt}>
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
          {busy ? "Wird vorbereitet…" : "Vorschlag erzeugen"}
        </button>
      </form>
    </div>
  );
}
