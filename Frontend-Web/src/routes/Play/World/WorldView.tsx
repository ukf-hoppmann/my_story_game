import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { WorldEntity, WorldState } from "../../../api/types";
import { Tabs } from "../../../components/Tabs/Tabs";
import { EntityDetail } from "./EntityDetail";
import { FactsTab } from "./FactsTab";
import { KnowledgeMatrix } from "./KnowledgeMatrix";
import { entitiesOfTab, entityTraits, knowledgeTurnRange, tabOfEntity, type EntityTabId, type TraitPart } from "./worldModel";
import "./WorldView.css";

type WorldTabId = EntityTabId | "facts" | "knowledge";
const ENTITY_TABS: EntityTabId[] = ["characters", "locations", "items", "others"];

export interface WorldViewProps {
  world: WorldState;
  /** The story's current turn sequence — the slider's default position. */
  currentTurn: number;
  trackingOff?: boolean;
}

/**
 * The Welt tab of the Play screen: topic tabs, per entity tab a list with
 * one or two main traits on the left and the full entry on the right.
 * Shows everything the world holds, including forgotten knowledge and
 * every visibility — nothing is hidden from the viewer yet.
 */
export function WorldView({ world, currentTurn, trackingOff = false }: WorldViewProps) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<WorldTabId>("characters");
  const [selection, setSelection] = useState<Partial<Record<EntityTabId, string>>>({});
  // null follows the newest turn, so a new turn moves the slider along.
  const [pinnedTurn, setPinnedTurn] = useState<number | null>(null);

  const range = knowledgeTurnRange(world, currentTurn);
  const turn = pinnedTurn === null ? range.max : Math.min(Math.max(pinnedTurn, range.min), range.max);
  const hasKnowledge = world.knowledge.length > 0;

  const counts: Record<WorldTabId, number> = {
    characters: entitiesOfTab(world, "characters").length,
    locations: entitiesOfTab(world, "locations").length,
    items: entitiesOfTab(world, "items").length,
    others: entitiesOfTab(world, "others").length,
    facts: world.facts.length,
    knowledge: world.knowledge.length,
  };
  const tabs = (["characters", "locations", "items", "others", "facts", "knowledge"] as WorldTabId[]).map((id) => ({
    id,
    label: t(`play.world.tabs.${id}`),
    count: counts[id],
  }));

  function openEntity(entity: WorldEntity) {
    const target = tabOfEntity(entity);
    setTab(target);
    setSelection((current) => ({ ...current, [target]: entity.id }));
  }

  return (
    <div className="world-view">
      <div className="world-head">
        <h1>{t("play.world.title")}</h1>
        {hasKnowledge && (
          <label className="world-slider">
            <span className="world-ctl-label">{t("play.world.turnLabel")}</span>
            <input
              type="range"
              min={range.min}
              max={range.max}
              value={turn}
              onChange={(event) => {
                const value = Number(event.target.value);
                setPinnedTurn(value >= range.max ? null : value);
              }}
            />
            <output>
              {turn >= currentTurn
                ? t("play.world.turnValueCurrent", { turn })
                : t("play.world.turnValue", { turn })}
            </output>
          </label>
        )}
      </div>
      {trackingOff && (
        <p className="world-note" role="note">
          {t("play.world.trackingOff")}
        </p>
      )}

      <Tabs tabs={tabs} activeId={tab} onChange={(id) => setTab(id as WorldTabId)} idPrefix="world">
        {ENTITY_TABS.includes(tab as EntityTabId) ? (
          <EntityBrowser
            world={world}
            tab={tab as EntityTabId}
            selectedId={selection[tab as EntityTabId]}
            onSelect={(id) => setSelection((current) => ({ ...current, [tab]: id }))}
            turn={turn}
            turnRange={range}
            onOpen={openEntity}
          />
        ) : tab === "facts" ? (
          <FactsTab world={world} turn={turn} onOpen={openEntity} />
        ) : (
          <KnowledgeMatrix world={world} turn={turn} />
        )}
      </Tabs>
    </div>
  );
}

interface EntityBrowserProps {
  world: WorldState;
  tab: EntityTabId;
  selectedId: string | undefined;
  onSelect: (id: string) => void;
  turn: number;
  turnRange: { min: number; max: number };
  onOpen: (entity: WorldEntity) => void;
}

function EntityBrowser({ world, tab, selectedId, onSelect, turn, turnRange, onOpen }: EntityBrowserProps) {
  const { t } = useTranslation();
  const entities = entitiesOfTab(world, tab);
  if (entities.length === 0) {
    return <p className="world-empty world-wide">{t(`play.world.empty.${tab}`)}</p>;
  }
  // A selection that left the world (or none yet) falls back to the first entry.
  const selected = entities.find((entity) => entity.id === selectedId) ?? entities[0];

  const renderTrait = (part: TraitPart) => ("text" in part ? part.text : t(part.key, part.params));

  return (
    <div className="world-browser">
      <nav className="world-list" aria-label={t("play.world.listLabel")}>
        {entities.map((entity) => (
          <button
            key={entity.id}
            type="button"
            className="world-list-item"
            aria-current={entity.id === selected.id}
            onClick={() => onSelect(entity.id)}
          >
            <span className="world-list-name">
              {entity.label}
              {entity.actor?.role === "player" && <span className="world-pill world-pill--player">{t("play.world.you")}</span>}
              {world.scene_location_ids.includes(entity.id) && (
                <span className="world-pill world-pill--scene">{t("play.world.scene")}</span>
              )}
            </span>
            <span className="world-list-trait">{entityTraits(world, entity).map(renderTrait).join(" · ")}</span>
          </button>
        ))}
      </nav>
      <EntityDetail world={world} entity={selected} turn={turn} turnRange={turnRange} onOpen={onOpen} />
    </div>
  );
}
