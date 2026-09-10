import { useTranslation } from "react-i18next";
import { Panel } from "../../components/Panel/Panel";
import { ImageSlot } from "../../components/ImageSlot/ImageSlot";
import { BookIcon, PersonIcon, TargetIcon, UsersIcon } from "../../icons";
import type { Fact, Goal, GoalStatus, ActorRole, WorldEntity } from "../../api/types";
import "./SidebarPanels.css";

const GOAL_STATUS_LABEL_KEYS: Record<GoalStatus, string> = {
  open: "play.goalStatus.open",
  completed: "play.goalStatus.completed",
  failed: "play.goalStatus.failed",
};

const ROLE_LABEL_KEYS: Record<ActorRole, string> = {
  player: "play.role.player",
  npc: "play.role.npc",
  neutral: "play.role.neutral",
};

/** Ziele. Deliberately title/description/status only — the backend's Goal
 *  model has no sub-steps/progress field (see plan discussion), so there is
 *  no progress bar here, unlike the original mockup. */
export function GoalsPanel({ goals }: { goals: Goal[] }) {
  const { t } = useTranslation();
  return (
    <Panel title={t("play.panels.goalsTitle")} icon={<TargetIcon />} className="sidebar-panel">
      {goals.length === 0 ? (
        <p className="sidebar-empty">{t("play.panels.noGoals")}</p>
      ) : (
        goals.map((goal) => (
          <div className="goal-block" key={goal.id}>
            <div className="goal-title">{goal.title}</div>
            <p className="goal-desc">{goal.description}</p>
            <span className={`status-pill status-pill--${goal.status}`}>
              {t(GOAL_STATUS_LABEL_KEYS[goal.status])}
            </span>
          </div>
        ))
      )}
    </Panel>
  );
}

/** Weltwissen. Full fact sentences, not short chip labels — the catalog has
 *  no short-label field yet (see plan discussion), so chips would need
 *  either an unreliable client-side truncation or a backend addition;
 *  both were deferred in favor of showing the real sentences now. */
export function FactsPanel({ facts }: { facts: Fact[] }) {
  const { t } = useTranslation();
  return (
    <Panel title={t("play.panels.factsTitle")} icon={<BookIcon />} className="sidebar-panel">
      {facts.length === 0 ? (
        <p className="sidebar-empty">{t("play.panels.noFacts")}</p>
      ) : (
        <ul className="fact-list">
          {facts.map((fact) => (
            <li key={fact.id}>{fact.statement}</li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

/** Figuren. Portraits are image-ready placeholders (Schritt 1's `ImageSlot`,
 *  circle shape) — swappable for real portraits later without layout
 *  changes, same pattern as the scene illustration. */
export function CharactersPanel({ entities }: { entities: WorldEntity[] }) {
  const { t } = useTranslation();
  const characters = entities.filter((entity) => entity.kind === "character");

  return (
    <Panel title={t("play.panels.charactersTitle")} icon={<UsersIcon />} className="sidebar-panel">
      {characters.length === 0 ? (
        <p className="sidebar-empty">{t("play.panels.noCharacters")}</p>
      ) : (
        characters.map((character) => (
          <div className="char-row" key={character.id}>
            <ImageSlot
              className="char-avatar"
              shape="circle"
              placeholderIcon={<PersonIcon />}
              label=""
            />
            <div className="char-body">
              <div className="char-name-row">
                <span className="char-name">{character.label}</span>
                {character.actor && (
                  <span className="char-role">{t(ROLE_LABEL_KEYS[character.actor.role])}</span>
                )}
              </div>
              {character.description && <div className="char-desc">{character.description}</div>}
            </div>
          </div>
        ))
      )}
    </Panel>
  );
}
