import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { Fact, KnowledgeEntry, WorldEntity, WorldState } from "../../../api/types";
import { knowersOf } from "./worldModel";

/** The fact's audience as a pill. Display only — the view filters nothing
 *  by visibility (TASK-049 notes): for now the owner sees everything. */
export function VisibilityPill({ fact, world }: { fact: Pick<Fact, "visibility">; world: WorldState }) {
  const { t } = useTranslation();
  const { scope, actor_id } = fact.visibility;
  const actor = actor_id ? world.entities.find((entity) => entity.id === actor_id) : undefined;
  const label = actor
    ? t("play.world.visibility.actor_knownNamed", { name: actor.label })
    : t(`play.world.visibility.${scope}`);
  return <span className={`world-vis world-vis--${scope}`}>{label}</span>;
}

/** Clickable entity name that opens the entity in its own tab. */
export function EntityLinkButton({ entity, onOpen }: { entity: WorldEntity; onOpen: (entity: WorldEntity) => void }) {
  return (
    <button type="button" className="world-link" onClick={() => onOpen(entity)}>
      {entity.label}
    </button>
  );
}

/** Who knows or knew a fact at `turn`, as chips. */
export function KnowersList({ world, factId, turn }: { world: WorldState; factId: string; turn: number }) {
  const { t } = useTranslation();
  const knowers = knowersOf(world, factId, turn);
  if (knowers.length === 0) {
    return <span className="world-nobody">{t("play.world.nobodyKnows")}</span>;
  }
  return (
    <>
      {knowers.map(({ entry, actor, status }) => (
        <span className={`world-who world-who--${status}`} key={actor.id}>
          <span className="world-dot" aria-hidden="true" />
          <span className="world-who-name">{actor.label}</span>
          <span>
            {status === "forgotten"
              ? t("play.world.knownSpan", { from: entry.learned_at, to: entry.forgotten_at })
              : t("play.world.knownSince", { turn: entry.learned_at })}
          </span>
        </span>
      ))}
    </>
  );
}

/** Horizontal bar over the slider's turn range: solid while the entry was
 *  known, dashed after it was forgotten, gold tick at the chosen turn. */
export function LifeBar({ entry, turn, range }: { entry: KnowledgeEntry; turn: number; range: { min: number; max: number } }) {
  const span = Math.max(range.max - range.min, 1);
  const pct = (value: number) => ((value - range.min) / span) * 100;
  const gone = entry.forgotten_at !== null && entry.forgotten_at <= turn;
  const knownEnd = gone ? (entry.forgotten_at as number) : turn;
  return (
    <div className="world-life" aria-hidden="true">
      <i
        className="world-life-known"
        style={{ left: `${pct(entry.learned_at)}%`, width: `${Math.max(pct(knownEnd) - pct(entry.learned_at), 1.5)}%` }}
      />
      {gone && (
        <i
          className="world-life-forgotten"
          style={{ left: `${pct(entry.forgotten_at as number)}%`, width: `${pct(turn) - pct(entry.forgotten_at as number)}%` }}
        />
      )}
      <span className="world-life-now" style={{ left: `calc(${pct(turn)}% - 1px)` }} />
    </div>
  );
}

/** Small uppercase heading with a rule and an optional count. */
export function SectionHeading({ children, count }: { children: ReactNode; count?: ReactNode }) {
  return (
    <h3 className="world-section-heading">
      {children}
      {count !== undefined && <span className="world-section-count">{count}</span>}
    </h3>
  );
}
