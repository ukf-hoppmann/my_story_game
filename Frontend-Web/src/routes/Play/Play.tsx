import { useLayoutEffect, useRef, useState } from "react";
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
import { ChatFeed } from "./ChatFeed";
import { SceneArt, SceneImageControls } from "./SceneArt";
import { CharactersPanel, FactsPanel, GoalsPanel } from "./SidebarPanels";
import "./Play.css";

type ViewMode = "text" | "chat";
const VIEW_MODE_KEY = "play.viewMode";

function loadViewMode(): ViewMode {
  try {
    return localStorage.getItem(VIEW_MODE_KEY) === "chat" ? "chat" : "text";
  } catch {
    return "text";
  }
}

function saveViewMode(mode: ViewMode) {
  try {
    localStorage.setItem(VIEW_MODE_KEY, mode);
  } catch {
    // Storage may be blocked; the choice then only lasts for this visit.
  }
}

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
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [activeTab, setActiveTab] = useState<PlayTab>("story");
  const [viewMode, setViewMode] = useState<ViewMode>(loadViewMode);
  const feedRef = useRef<HTMLDivElement>(null);
  // The story turn at the top of the flowing-text feed; undefined while the
  // feed sits at its end, where the newest picture belongs.
  const [visibleTurn, setVisibleTurn] = useState<number | undefined>(undefined);
  // Suggested next moves from the most recent `playTurn` response. Transient
  // presentation data (TASK-034) — never part of `GameDocument`, so it is
  // held locally here rather than read back from the reloaded state.
  const [continuationOptions, setContinuationOptions] = useState<string[]>([]);
  const [activeOption, setActiveOption] = useState<string | null>(null);

  const { data: doc, isLoading, error, refetch } = useLoadRunQuery(runId, { skip: runId === "" });
  const [playTurn, playTurnState] = usePlayTurnMutation();
  const [startPlaythrough, startState] = useStartPlaythroughMutation();

  // Grow the field with its content; the CSS max-height caps it and lets the
  // rest scroll. Reset first so the field also shrinks again.
  useLayoutEffect(() => {
    const field = inputRef.current;
    if (!field) {
      return;
    }
    field.style.height = "auto";
    field.style.height = `${field.scrollHeight}px`;
  }, [input, doc]);

  // Like a chat: land on the newest turn on load, on a new turn and on a switch.
  const turnCount = doc?.game_state.story.turns.length;
  const hasFeed = doc?.game_run.status === "active";
  useLayoutEffect(() => {
    const feed = feedRef.current;
    if (feed) {
      feed.scrollTop = feed.scrollHeight;
    }
    setVisibleTurn(undefined);
  }, [turnCount, hasFeed, viewMode, activeTab]);

  function handleFeedScroll() {
    const feed = feedRef.current;
    if (!feed) {
      return;
    }
    if (feed.scrollTop + feed.clientHeight >= feed.scrollHeight - 4) {
      setVisibleTurn(undefined);
      return;
    }
    const lineY = feed.getBoundingClientRect().top + 40;
    let current = 0;
    for (const element of feed.querySelectorAll<HTMLElement>("[data-turn]")) {
      if (element.getBoundingClientRect().top > lineY) {
        break;
      }
      current = Number(element.dataset.turn);
    }
    setVisibleTurn(current);
  }

  function handleToggleViewMode() {
    const next: ViewMode = viewMode === "text" ? "chat" : "text";
    setViewMode(next);
    saveViewMode(next);
  }

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
              <div className="play-scene-header-actions">
                <Button variant="ghost" aria-pressed={viewMode === "chat"} onClick={handleToggleViewMode}>
                  {viewMode === "chat" ? t("play.viewMode.toText") : t("play.viewMode.toChat")}
                </Button>
                <span className="play-turn-badge">
                  {t("play.turnBadge", { turn: doc.game_state.story.current_turn_sequence })}
                </span>
              </div>
            </div>

            {viewMode === "text" && (
              <SceneArt runId={runId} name={doc.game_run.name} turn={visibleTurn} />
            )}

            {activeTab === "story" && viewMode === "text" && (
              <div className="play-story-feed" ref={feedRef} onScroll={handleFeedScroll}>
                {doc.game_state.story.initialization && (
                  <div className="play-turn" data-turn={0}>
                    <Paragraphs text={doc.game_state.story.initialization.narration} />
                  </div>
                )}
                {doc.game_state.story.turns.map((turn) => (
                  <div className="play-turn" data-turn={turn.sequence} key={turn.id}>
                    <p className="play-turn-input">{t("play.turnInputPrefix", { input: turn.player_input })}</p>
                    <Paragraphs text={turn.narration} />
                  </div>
                ))}
              </div>
            )}

            {activeTab === "story" && viewMode === "chat" && (
              <>
                <div className="play-story-feed play-chat" ref={feedRef}>
                  <ChatFeed runId={runId} story={doc.game_state.story} name={doc.game_run.name} />
                </div>
                <SceneImageControls runId={runId} />
              </>
            )}

            {activeTab === "chronicle" && (
              <div className="play-story-feed play-chronicle" ref={feedRef}>
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
                <textarea
                  ref={inputRef}
                  rows={1}
                  placeholder={t("play.actionPlaceholder")}
                  value={input}
                  onChange={(event) => handleInputChange(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
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
