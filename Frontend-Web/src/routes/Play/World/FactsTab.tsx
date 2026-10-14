import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { VisibilityScope, WorldEntity, WorldState } from "../../../api/types";
import { EntityLinkButton, KnowersList, SectionHeading, VisibilityPill } from "./WorldParts";

type ScopeFilter = "all" | VisibilityScope;
const SCOPE_FILTERS: ScopeFilter[] = ["all", "public", "player_known", "actor_known", "director_only"];

export interface FactsTabProps {
  world: WorldState;
  turn: number;
  onOpen: (entity: WorldEntity) => void;
}

/** All facts with what they concern and who knows them, then the world rules. */
export function FactsTab({ world, turn, onOpen }: FactsTabProps) {
  const { t } = useTranslation();
  const [scope, setScope] = useState<ScopeFilter>("all");
  const facts = world.facts.filter((fact) => scope === "all" || fact.visibility.scope === scope);

  return (
    <div className="world-wide">
      <div className="world-filter-row">
        <span className="world-ctl-label">{t("play.world.visibilityLabel")}</span>
        <div className="world-seg" role="group" aria-label={t("play.world.visibilityLabel")}>
          {SCOPE_FILTERS.map((value) => (
            <button key={value} type="button" aria-pressed={scope === value} onClick={() => setScope(value)}>
              {t(`play.world.visibility.${value}`)}
            </button>
          ))}
        </div>
      </div>

      <section>
        <SectionHeading count={facts.length}>{t("play.world.sections.facts")}</SectionHeading>
        {facts.length === 0 ? (
          <p className="world-empty">{world.facts.length === 0 ? t("play.world.noFacts") : t("play.world.noEntriesForFilter")}</p>
        ) : (
          <div className="world-facts">
            {facts.map((fact) => {
              const subject = world.entities.find((entity) => entity.id === fact.subject_id);
              return (
                <div className="world-fact" key={fact.id}>
                  <div className="world-fact-statement">{fact.statement}</div>
                  <div>
                    <VisibilityPill fact={fact} world={world} />
                  </div>
                  <div className="world-fact-sub">
                    <span className="world-fact-label">{t("play.world.subject")}</span>
                    {subject ? <EntityLinkButton entity={subject} onOpen={onOpen} /> : <span>{t("play.world.noSubject")}</span>}
                  </div>
                  <div className="world-fact-sub">
                    <span className="world-fact-label">{t("play.world.knowers")}</span>
                    <KnowersList world={world} factId={fact.id} turn={turn} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section>
        <SectionHeading count={world.rules.length}>{t("play.world.sections.rules")}</SectionHeading>
        {world.rules.length === 0 ? (
          <p className="world-empty">{t("play.world.noRules")}</p>
        ) : (
          <div className="world-facts">
            {world.rules.map((rule) => (
              <div className="world-fact" key={rule.id}>
                <div className="world-fact-statement">{rule.statement}</div>
                <div>
                  <VisibilityPill fact={rule} world={world} />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
