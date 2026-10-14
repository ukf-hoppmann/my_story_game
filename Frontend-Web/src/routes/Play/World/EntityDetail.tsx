import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { EntityKind, WorldEntity, WorldState } from "../../../api/types";
import { ImageSlot } from "../../../components/ImageSlot/ImageSlot";
import { BannerIcon, KeyIcon, MapPinIcon, PawIcon, PersonIcon } from "../../../icons";
import { factsAbout, knowledgeOf, relationsOf, type KnowledgeStatus } from "./worldModel";
import { EntityLinkButton, KnowersList, LifeBar, SectionHeading, VisibilityPill } from "./WorldParts";

const KIND_ICON: Record<EntityKind, typeof PersonIcon> = {
  character: PersonIcon,
  location: MapPinIcon,
  item: KeyIcon,
  creature: PawIcon,
  faction: BannerIcon,
};

type KnowledgeFilter = "all" | Exclude<KnowledgeStatus, "future">;
const FILTERS: KnowledgeFilter[] = ["all", "known", "forgotten"];

export interface EntityDetailProps {
  world: WorldState;
  entity: WorldEntity;
  turn: number;
  turnRange: { min: number; max: number };
  onOpen: (entity: WorldEntity) => void;
}

/** Everything the world holds about one entity: description, conditions,
 *  relations, its own knowledge (actors only) and the facts about it. */
export function EntityDetail({ world, entity, turn, turnRange, onOpen }: EntityDetailProps) {
  const { t } = useTranslation();
  const Icon = KIND_ICON[entity.kind];
  const relations = relationsOf(world, entity.id);
  const about = factsAbout(world, entity.id);
  const isScene = world.scene_location_ids.includes(entity.id);
  // Characters always get the section, so an empty one says plainly that no
  // knowledge is recorded yet (the backend does not fill it yet, TASK-049).
  const holdsKnowledge =
    entity.kind === "character" || world.knowledge.some((entry) => entry.actor_id === entity.id);

  return (
    <article className="world-detail">
      <div className="world-detail-head">
        <ImageSlot
          className={entity.kind === "character" ? "world-avatar" : "world-avatar world-avatar--square"}
          shape="circle"
          placeholderIcon={<Icon />}
          label=""
        />
        <div>
          <h2>{entity.label}</h2>
          <div className="world-detail-sub">
            <span className={entity.actor?.role === "player" ? "world-pill world-pill--player" : "world-pill"}>
              {entity.actor ? t(`play.role.${entity.actor.role}`) : t(`play.world.kind.${entity.kind}`)}
            </span>
            {isScene && <span className="world-pill world-pill--scene">{t("play.world.currentScene")}</span>}
            {entity.aliases.length > 0 && <span>{t("play.world.aliases", { names: entity.aliases.join(", ") })}</span>}
          </div>
        </div>
      </div>

      {entity.description && <p className="world-desc">{entity.description}</p>}

      {entity.conditions.length > 0 && (
        <section>
          <SectionHeading count={entity.conditions.length}>{t("play.world.sections.conditions")}</SectionHeading>
          <div className="world-conditions">
            {entity.conditions.map((condition) => (
              <div className="world-condition" key={condition.name}>
                <b>{condition.name}</b>
                {condition.description && <span>{condition.description}</span>}
              </div>
            ))}
          </div>
        </section>
      )}

      <section>
        <SectionHeading count={relations.length}>{t("play.world.sections.relations")}</SectionHeading>
        {relations.length === 0 ? (
          <p className="world-empty">{t("play.world.noRelations")}</p>
        ) : (
          <div className="world-relations">
            {relations.map(({ link, direction, other }) => (
              <div className="world-relation" key={link.id}>
                <span className="world-relation-kind">{t(`play.world.relation.${link.kind}.${direction}`)}</span>
                <span>
                  <EntityLinkButton entity={other} onOpen={onOpen} />
                  {link.quantity !== null && link.quantity !== 1 && (
                    <span className="world-quantity">{t("play.world.quantity", { count: link.quantity })}</span>
                  )}
                </span>
                {link.description && <span className="world-relation-note">{link.description}</span>}
              </div>
            ))}
          </div>
        )}
      </section>

      {holdsKnowledge && <KnowledgeSection world={world} entity={entity} turn={turn} turnRange={turnRange} />}

      <section>
        <SectionHeading count={about.length}>{t("play.world.sections.factsAbout", { name: entity.label })}</SectionHeading>
        {about.length === 0 ? (
          <p className="world-empty">{t("play.world.noFactsAbout")}</p>
        ) : (
          <div className="world-facts">
            {about.map((fact) => (
              <div className="world-fact" key={fact.id}>
                <div className="world-fact-statement">{fact.statement}</div>
                <div>
                  <VisibilityPill fact={fact} world={world} />
                </div>
                <div className="world-fact-sub">
                  <span className="world-fact-label">{t("play.world.knowers")}</span>
                  <KnowersList world={world} factId={fact.id} turn={turn} />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </article>
  );
}

function KnowledgeSection({ world, entity, turn, turnRange }: Omit<EntityDetailProps, "onOpen">) {
  const { t } = useTranslation();
  const [filter, setFilter] = useState<KnowledgeFilter>("all");
  const entries = knowledgeOf(world, entity.id, turn);
  const known = entries.filter((item) => item.status === "known").length;
  const shown = entries.filter((item) => filter === "all" || item.status === filter);

  return (
    <section>
      <div className="world-knowledge-head">
        <SectionHeading count={t("play.world.knowledgeCounts", { known, forgotten: entries.length - known })}>
          {t("play.world.sections.knowledge")}
        </SectionHeading>
        {entries.length > 0 && (
          <div className="world-seg" role="group" aria-label={t("play.world.filterLabel")}>
            {FILTERS.map((value) => (
              <button key={value} type="button" aria-pressed={filter === value} onClick={() => setFilter(value)}>
                {t(`play.world.filter.${value}`)}
              </button>
            ))}
          </div>
        )}
      </div>
      {entries.length === 0 ? (
        <p className="world-empty">{t("play.world.noKnowledge")}</p>
      ) : shown.length === 0 ? (
        <p className="world-empty">{t("play.world.noEntriesForFilter")}</p>
      ) : (
        <ul className="world-knowledge-list">
          {shown.map(({ entry, fact, status }) => (
            <li className={`world-knowledge-item world-knowledge-item--${status}`} key={fact.id}>
              <div className="world-knowledge-statement">{fact.statement}</div>
              <div className="world-knowledge-meta">
                <span className="world-learned">{t("play.world.learnedAt", { turn: entry.learned_at })}</span>
                {status === "forgotten" && (
                  <span className="world-forgotten">{t("play.world.forgottenAt", { turn: entry.forgotten_at })}</span>
                )}
                <VisibilityPill fact={fact} world={world} />
              </div>
              <LifeBar entry={entry} turn={turn} range={turnRange} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
