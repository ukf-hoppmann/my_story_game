import { useTranslation } from "react-i18next";
import type { WorldState } from "../../../api/types";
import { actorsWithKnowledge, knowledgeStatusAt } from "./worldModel";
import { VisibilityPill } from "./WorldParts";

/** Facts as rows, knowing actors as columns: who knows what since when. */
export function KnowledgeMatrix({ world, turn }: { world: WorldState; turn: number }) {
  const { t } = useTranslation();
  const actors = actorsWithKnowledge(world);

  if (actors.length === 0) {
    return (
      <div className="world-wide">
        <p className="world-empty">{t("play.world.matrix.empty")}</p>
      </div>
    );
  }

  return (
    <div className="world-wide">
      <div className="world-legend">
        <span>
          <i className="world-dot" aria-hidden="true" />
          {t("play.world.matrix.legendKnown")}
        </span>
        <span>
          <i className="world-dot world-dot--forgotten" aria-hidden="true" />
          {t("play.world.matrix.legendForgotten")}
        </span>
        <span>· {t("play.world.matrix.legendNone")}</span>
      </div>
      <div className="world-matrix-wrap">
        <table className="world-matrix">
          <thead>
            <tr>
              <th className="world-matrix-fact">{t("play.world.matrix.fact")}</th>
              {actors.map((actor) => (
                <th key={actor.id}>{actor.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {world.facts.map((fact) => (
              <tr key={fact.id}>
                <td className="world-matrix-fact">
                  {fact.statement} <VisibilityPill fact={fact} world={world} />
                </td>
                {actors.map((actor) => {
                  const entry = world.knowledge.find((item) => item.fact_id === fact.id && item.actor_id === actor.id);
                  const status = entry ? knowledgeStatusAt(entry, turn) : "future";
                  if (!entry || status === "future") {
                    return (
                      <td key={actor.id}>
                        <span className="world-cell world-cell--none">·</span>
                      </td>
                    );
                  }
                  return (
                    <td key={actor.id}>
                      <span
                        className={`world-cell world-cell--${status}`}
                        title={t(status === "forgotten" ? "play.world.matrix.statusForgotten" : "play.world.matrix.statusKnown")}
                      >
                        <i className={status === "forgotten" ? "world-dot world-dot--forgotten" : "world-dot"} aria-hidden="true" />
                        {status === "forgotten"
                          ? t("play.world.matrix.cellForgotten", { from: entry.learned_at, to: entry.forgotten_at })
                          : t("play.world.matrix.cellKnown", { turn: entry.learned_at })}
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
