import type { EntityKind, EntityLink, Fact, KnowledgeEntry, WorldEntity, WorldState } from "../../../api/types";

/**
 * Read-only derivations for the Welt view. Everything here works on the
 * `WorldState` the run document already carries — the view needs no
 * endpoint of its own. Kept free of React so the rules (when an entry
 * counts as known, what the list shows per entity) are testable alone.
 */

export type EntityTabId = "characters" | "locations" | "items" | "others";

const TAB_OF_KIND: Record<EntityKind, EntityTabId> = {
  character: "characters",
  location: "locations",
  item: "items",
  creature: "others",
  faction: "others",
};

export function tabOfEntity(entity: WorldEntity): EntityTabId {
  return TAB_OF_KIND[entity.kind];
}

export function entitiesOfTab(world: WorldState, tab: EntityTabId): WorldEntity[] {
  return world.entities.filter((entity) => TAB_OF_KIND[entity.kind] === tab);
}

/** "future": not learned yet at that turn, so not shown at all. */
export type KnowledgeStatus = "future" | "known" | "forgotten";

/** `learned_at`/`forgotten_at` are story-turn sequence numbers; an entry
 *  forgotten in turn N counts as forgotten from N on. */
export function knowledgeStatusAt(entry: KnowledgeEntry, turn: number): KnowledgeStatus {
  if (entry.learned_at > turn) {
    return "future";
  }
  if (entry.forgotten_at !== null && entry.forgotten_at <= turn) {
    return "forgotten";
  }
  return "known";
}

/** Turn range the "Wissensstand bei" slider covers. Turns start at 1. */
export function knowledgeTurnRange(world: WorldState, currentTurn: number): { min: number; max: number } {
  let max = Math.max(currentTurn, 1);
  for (const entry of world.knowledge) {
    max = Math.max(max, entry.learned_at, entry.forgotten_at ?? 0);
  }
  return { min: 1, max };
}

export interface ActorKnowledge {
  entry: KnowledgeEntry;
  fact: Fact;
  status: Exclude<KnowledgeStatus, "future">;
}

/** What one actor knows or has forgotten at `turn`, oldest first. */
export function knowledgeOf(world: WorldState, actorId: string, turn: number): ActorKnowledge[] {
  const result: ActorKnowledge[] = [];
  for (const entry of world.knowledge) {
    const fact = world.facts.find((item) => item.id === entry.fact_id);
    const status = knowledgeStatusAt(entry, turn);
    if (entry.actor_id === actorId && fact && status !== "future") {
      result.push({ entry, fact, status });
    }
  }
  return result.sort((a, b) => a.entry.learned_at - b.entry.learned_at);
}

export interface FactKnower {
  entry: KnowledgeEntry;
  actor: WorldEntity;
  status: Exclude<KnowledgeStatus, "future">;
}

/** Who knows or knew a fact at `turn`, in learning order. */
export function knowersOf(world: WorldState, factId: string, turn: number): FactKnower[] {
  const result: FactKnower[] = [];
  for (const entry of world.knowledge) {
    const actor = world.entities.find((item) => item.id === entry.actor_id);
    const status = knowledgeStatusAt(entry, turn);
    if (entry.fact_id === factId && actor && status !== "future") {
      result.push({ entry, actor, status });
    }
  }
  return result.sort((a, b) => a.entry.learned_at - b.entry.learned_at);
}

export function factsAbout(world: WorldState, entityId: string): Fact[] {
  return world.facts.filter((fact) => fact.subject_id === entityId);
}

/** Entities that hold at least one knowledge entry — the matrix columns. */
export function actorsWithKnowledge(world: WorldState): WorldEntity[] {
  const ids = new Set(world.knowledge.map((entry) => entry.actor_id));
  return world.entities.filter((entity) => ids.has(entity.id));
}

export interface Relation {
  link: EntityLink;
  direction: "outgoing" | "incoming";
  other: WorldEntity;
}

/** Links touching an entity, each with the entity at its other end. Links
 *  pointing at an entity that is no longer in the world are skipped. */
export function relationsOf(world: WorldState, entityId: string): Relation[] {
  const result: Relation[] = [];
  for (const link of world.links) {
    const direction = link.source_id === entityId ? "outgoing" : link.target_id === entityId ? "incoming" : null;
    if (direction === null) {
      continue;
    }
    const otherId = direction === "outgoing" ? link.target_id : link.source_id;
    const other = world.entities.find((item) => item.id === otherId);
    if (other) {
      result.push({ link, direction, other });
    }
  }
  return result;
}

/** One piece of the short description under a name in the list: either
 *  world text as is, or an i18n key with its parameters. */
export type TraitPart = { text: string } | { key: string; params?: Record<string, string | number> };

function linkedLabel(world: WorldState, entityId: string, kind: EntityLink["kind"], direction: "outgoing" | "incoming") {
  return relationsOf(world, entityId).find((relation) => relation.link.kind === kind && relation.direction === direction)
    ?.other.label;
}

/** The one or two main traits the list shows next to each name. */
export function entityTraits(world: WorldState, entity: WorldEntity): TraitPart[] {
  const conditionNames = entity.conditions.map((condition) => condition.name);

  if (entity.kind === "character") {
    const parts: TraitPart[] = [];
    const location = linkedLabel(world, entity.id, "located_in", "outgoing");
    if (location) {
      parts.push({ text: location });
    }
    if (conditionNames.length > 0) {
      parts.push({ text: conditionNames.join(", ") });
    }
    return parts.length > 0 ? parts : [{ key: "play.world.traits.whereaboutsUnknown" }];
  }

  if (entity.kind === "location") {
    const parts: TraitPart[] = conditionNames.length > 0 ? [{ text: conditionNames[0] }] : [];
    const present = relationsOf(world, entity.id).filter(
      (relation) => relation.link.kind === "located_in" && relation.direction === "incoming",
    ).length;
    const container = linkedLabel(world, entity.id, "contains", "incoming");
    if (present > 0) {
      parts.push({ key: "play.world.traits.presentCount", params: { count: present } });
    } else if (container) {
      parts.push({ key: "play.world.traits.inside", params: { name: container } });
    } else {
      parts.push({ key: "play.world.traits.nobodyHere" });
    }
    return parts;
  }

  if (entity.kind === "item") {
    const owner = linkedLabel(world, entity.id, "possesses", "incoming");
    if (owner) {
      return [{ key: "play.world.traits.heldBy", params: { name: owner } }];
    }
    const place =
      linkedLabel(world, entity.id, "contains", "incoming") ?? linkedLabel(world, entity.id, "located_in", "outgoing");
    if (place) {
      return [{ key: "play.world.traits.inside", params: { name: place } }];
    }
    return [{ key: "play.world.traits.whereaboutsUnknown" }];
  }

  const parts: TraitPart[] = [{ key: `play.world.kind.${entity.kind}` }];
  if (conditionNames.length > 0) {
    parts.push({ text: conditionNames[0] });
  }
  return parts;
}
