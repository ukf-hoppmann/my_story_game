import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useLoadRunQuery, usePlayTurnMutation, useStartPlaythroughMutation } from "../../api/apiSlice";
import { Paragraphs } from "../../components/Paragraphs";
import { Button } from "../../components/Button/Button";
import { ImageSlot } from "../../components/ImageSlot/ImageSlot";
import {
  ArrowRightIcon,
  BookIcon,
  CompassIcon,
  GlobeIcon,
  ScrollIcon,
  TargetIcon,
} from "../../icons";
import { CharactersPanel, FactsPanel, GoalsPanel } from "./SidebarPanels";
import "./Play.css";

/** Recovery copy for the error codes the old PlayScreen specifically
 *  handled — a stale run or a concurrent-edit conflict both need a reload,
 *  not just "something went wrong". */
const TURN_ERROR_KEYS: Record<string, string> = {
  run_not_active: "play.errors.runNotActive",
  revision_conflict: "play.errors.revisionConflict",
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
  const { t } = useTranslation();
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
          <span className="play-brand-name">{doc?.game_run.name ?? t("play.brandFallback")}</span>
        </div>

        <nav className="play-nav">
          <div className="play-nav-item play-nav-item--active">
            <BookIcon />
            {t("play.nav.story")}
          </div>
          <div className="play-nav-item">
            <GlobeIcon />
            {t("play.nav.world")}
          </div>
          <div className="play-nav-item">
            <TargetIcon />
            {t("play.nav.goals")}
          </div>
          <div className="play-nav-item">
            <ScrollIcon />
            {t("play.nav.chronicle")}
          </div>
        </nav>

        <div className="play-rail-foot">{t("play.railQuote")}</div>
      </aside>

      <main className="play-stage">
        {isLoading && <p className="play-status">{t("play.loading")}</p>}

        {error && (
          <div className="play-error-banner">
            <span>{t("play.loadError")}</span>
            <Button variant="ghost" onClick={() => refetch()}>
              {t("common.retry")}
            </Button>
          </div>
        )}

        {doc && doc.game_run.status !== "active" && (
          <div className="play-draft-banner">
            <p>{t("play.draftBanner")}</p>
            {startState.error && <p className="play-status">{t("play.startError")}</p>}
            <Button
              icon={<ArrowRightIcon />}
              disabled={startState.isLoading}
              onClick={handleStartPlaythrough}
            >
              {startState.isLoading ? t("play.starting") : t("play.startGame")}
            </Button>
          </div>
        )}

        {doc && doc.game_run.status === "active" && (
          <>
            <div className="play-scene-header">
              <h1>{doc.game_run.name}</h1>
              <span className="play-turn-badge">
                {t("play.turnBadge", { turn: doc.game_state.story.current_turn_sequence })}
              </span>
            </div>

            <ImageSlot
              className="play-scene-art"
              label={t("play.sceneArtPlaceholder")}
              alt={doc.game_run.name}
            />

            <div className="play-story-feed">
              {doc.game_state.story.initialization && (
                <div className="play-turn">
                  <Paragraphs text={doc.game_state.story.initialization.narration} />
                </div>
              )}
              {doc.game_state.story.turns.map((turn) => (
                <div className="play-turn" key={turn.id}>
                  <p className="play-turn-input">{t("play.turnInputPrefix", { input: turn.player_input })}</p>
                  <Paragraphs text={turn.narration} />
                </div>
              ))}
            </div>

            {playTurnState.error && (
              <div className="play-error-banner">
                <span>
                  {(() => {
                    const code = errorCode(playTurnState.error);
                    return t((code && TURN_ERROR_KEYS[code]) ?? "play.errors.generic");
                  })()}
                </span>
                <Button variant="ghost" onClick={() => refetch()}>
                  {t("play.reload")}
                </Button>
              </div>
            )}

            <div className="play-action-row">
              <label className="play-action-input">
                <input
                  type="text"
                  placeholder={t("play.actionPlaceholder")}
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
                {playTurnState.isLoading ? t("play.submitting") : t("play.submitTurn")}
              </Button>
            </div>
          </>
        )}
      </main>

      <aside className="play-sidebar">
        {doc ? (
          <>
            <GoalsPanel goals={doc.game_state.world.goals} />
            <FactsPanel facts={doc.game_state.world.facts} />
            <CharactersPanel entities={doc.game_state.world.entities} />
          </>
        ) : (
          <p className="play-sidebar-note">{t("play.sidebarNote")}</p>
        )}
      </aside>
    </div>
  );
}
