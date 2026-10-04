import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useLoadRunQuery, usePlayTurnMutation, useStartPlaythroughMutation } from "../../api/apiSlice";
import { toQueryError } from "../../api/queryError";
import { Paragraphs } from "../../components/Paragraphs";
import { Button } from "../../components/Button/Button";
import { Chip } from "../../components/Chip/Chip";
import {
  ArrowRightIcon,
  BookIcon,
  CompassIcon,
  GlobeIcon,
  ScrollIcon,
  TargetIcon,
} from "../../icons";
import { ErrorBanner } from "../../components/ErrorBanner/ErrorBanner";
import { SceneArt } from "./SceneArt";
import { CharactersPanel, FactsPanel, GoalsPanel } from "./SidebarPanels";
import "./Play.css";

/** Recovery copy for the error codes the old PlayScreen specifically
 *  handled — a stale run or a concurrent-edit conflict both need a reload,
 *  not just "something went wrong". Consumed by `ErrorBanner`'s
 *  `knownCodes` prop. */
const TURN_ERROR_KEYS: Record<string, string> = {
  run_not_active: "play.errors.runNotActive",
  revision_conflict: "play.errors.revisionConflict",
};

type PlayTab = "story" | "chronicle";

export function Play() {
  const { t } = useTranslation();
  const { runId = "" } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [input, setInput] = useState("");
  const [activeTab, setActiveTab] = useState<PlayTab>("story");
  // Suggested next moves from the most recent `playTurn` response. Transient
  // presentation data (TASK-034) — never part of `GameDocument`, so it is
  // held locally here rather than read back from the reloaded state.
  const [continuationOptions, setContinuationOptions] = useState<string[]>([]);
  const [activeOption, setActiveOption] = useState<string | null>(null);

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
      setActiveOption(null);
      setContinuationOptions(result.data.continuation.options);
    }
  }

  function handleInputChange(value: string) {
    setInput(value);
    if (value !== activeOption) {
      setActiveOption(null);
    }
  }

  function handleOptionClick(option: string) {
    if (option === activeOption) {
      handleSubmitTurn();
      return;
    }
    setInput(option);
    setActiveOption(option);
  }

  async function handleStartPlaythrough() {
    try {
      const active = await startPlaythrough(runId).unwrap();
      navigate(`/stories/${active.game_run.id}`);
    } catch (error) {
      // startState.error below already covers the mutation's own rejection;
      // this only still matters for a synchronous exception thrown before
      // the request was dispatched, which unwrap() never produces itself.
      if (!(error instanceof Object && "status" in error)) {
        toQueryError(error, "play.handleStartPlaythrough");
      }
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
          <div
            className={`play-nav-item${activeTab === "story" ? " play-nav-item--active" : ""}`}
            onClick={() => setActiveTab("story")}
            role="button"
            tabIndex={0}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                setActiveTab("story");
              }
            }}
          >
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
          <div
            className={`play-nav-item${activeTab === "chronicle" ? " play-nav-item--active" : ""}`}
            onClick={() => setActiveTab("chronicle")}
            role="button"
            tabIndex={0}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                setActiveTab("chronicle");
              }
            }}
          >
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
            <span>
              <ErrorBanner error={error} fallbackKey="play.loadError" bare />
            </span>
            <Button variant="ghost" onClick={() => refetch()}>
              {t("common.retry")}
            </Button>
          </div>
        )}

        {doc && doc.game_run.status !== "active" && (
          <div className="play-draft-banner">
            <p>{t("play.draftBanner")}</p>
            <ErrorBanner error={startState.error} fallbackKey="play.startError" className="play-status" />
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

            <SceneArt runId={runId} name={doc.game_run.name} />

            {activeTab === "story" && (
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
            )}

            {activeTab === "chronicle" && (
              <div className="play-story-feed play-chronicle">
                {doc.game_state.story.summaries.length === 0 ? (
                  <p className="play-status">{t("play.chronicle.empty")}</p>
                ) : (
                  doc.game_state.story.summaries.map((segment) => (
                    <div className="play-turn" key={segment.through_sequence}>
                      <Paragraphs text={segment.text} />
                    </div>
                  ))
                )}
              </div>
            )}

            {playTurnState.error && (
              <div className="play-error-banner">
                <span>
                  <ErrorBanner
                    error={playTurnState.error}
                    knownCodes={TURN_ERROR_KEYS}
                    fallbackKey="play.errors.generic"
                    bare
                  />
                </span>
                <Button variant="ghost" onClick={() => refetch()}>
                  {t("play.reload")}
                </Button>
              </div>
            )}

            {continuationOptions.length > 0 && (
              <div className="play-continuation-chips">
                {continuationOptions.map((option) => (
                  <Chip key={option} selected={option === activeOption} onClick={() => handleOptionClick(option)}>
                    {option}
                  </Chip>
                ))}
              </div>
            )}

            <div className="play-action-row">
              <label className="play-action-input">
                <input
                  type="text"
                  placeholder={t("play.actionPlaceholder")}
                  value={input}
                  onChange={(event) => handleInputChange(event.target.value)}
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
