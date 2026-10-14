import { describe, expect, it } from "vitest";
import type { EntityLink, Fact, KnowledgeEntry, WorldEntity, WorldState } from "../../../api/types";
import {
  actorsWithKnowledge,
  entitiesOfTab,
  entityTraits,
  factsAbout,
  knowersOf,
  knowledgeOf,
  knowledgeStatusAt,
  knowledgeTurnRange,
  relationsOf,
} from "./worldModel";

function entity(id: string, kind: WorldEntity["kind"], extra: Partial<WorldEntity> = {}): WorldEntity {
  return { id, kind, label: id, description: "", actor: null, conditions: [], aliases: [], ...extra };
}

function link(source_id: string, target_id: string, kind: EntityLink["kind"]): EntityLink {
  return {
    id: `${source_id}-${kind}-${target_id}`,
    source_id,
    target_id,
    kind,
    visibility: { scope: "public", actor_id: null },
    quantity: null,
    description: null,
  };
}

function fact(id: string, subject_id: string | null = null): Fact {
  return { id, statement: `Satz ${id}`, visibility: { scope: "public", actor_id: null }, subject_id };
}

function know(actor_id: string, fact_id: string, learned_at: number, forgotten_at: number | null = null): KnowledgeEntry {
  return { actor_id, fact_id, learned_at, forgotten_at };
}

function world(overrides: Partial<WorldState>): WorldState {
  return {
    entities: [],
    links: [],
    facts: [],
    knowledge: [],
    rules: [],
    goals: [],
    scene_location_ids: [],
    ...overrides,
  };
}

describe("knowledgeStatusAt", () => {
  const entry = know("a", "f", 3, 7);

  it("is future before the turn it was learned", () => {
    expect(knowledgeStatusAt(entry, 2)).toBe("future");
  });

  it("is known from the learning turn until before the forgetting turn", () => {
    expect(knowledgeStatusAt(entry, 3)).toBe("known");
    expect(knowledgeStatusAt(entry, 6)).toBe("known");
  });

  it("is forgotten from the forgetting turn on", () => {
    expect(knowledgeStatusAt(entry, 7)).toBe("forgotten");
    expect(knowledgeStatusAt(entry, 20)).toBe("forgotten");
  });

  it("stays known when never forgotten", () => {
    expect(knowledgeStatusAt(know("a", "f", 1), 99)).toBe("known");
  });
});

describe("knowledgeTurnRange", () => {
  it("spans from turn 1 to the current turn", () => {
    expect(knowledgeTurnRange(world({}), 12)).toEqual({ min: 1, max: 12 });
  });

  it("never ends before a recorded learning or forgetting turn", () => {
    const w = world({ knowledge: [know("a", "f", 4, 15)] });
    expect(knowledgeTurnRange(w, 9)).toEqual({ min: 1, max: 15 });
  });

  it("has at least one turn before the first turn is played", () => {
    expect(knowledgeTurnRange(world({}), 0)).toEqual({ min: 1, max: 1 });
  });
});

describe("entitiesOfTab", () => {
  it("groups creatures and factions together and keeps the world order", () => {
    const w = world({
      entities: [
        entity("wolf", "creature"),
        entity("mara", "character"),
        entity("velmar", "faction"),
        entity("krug", "location"),
        entity("ring", "item"),
      ],
    });
    expect(entitiesOfTab(w, "characters").map((e) => e.id)).toEqual(["mara"]);
    expect(entitiesOfTab(w, "locations").map((e) => e.id)).toEqual(["krug"]);
    expect(entitiesOfTab(w, "items").map((e) => e.id)).toEqual(["ring"]);
    expect(entitiesOfTab(w, "others").map((e) => e.id)).toEqual(["wolf", "velmar"]);
  });
});

describe("relationsOf", () => {
  it("lists outgoing and incoming links with the entity at the other end", () => {
    const w = world({
      entities: [entity("mara", "character"), entity("krug", "location"), entity("hedda", "character")],
      links: [link("mara", "krug", "located_in"), link("hedda", "mara", "knows")],
    });
    const relations = relationsOf(w, "mara");
    expect(relations.map((r) => [r.direction, r.other.id, r.link.kind])).toEqual([
      ["outgoing", "krug", "located_in"],
      ["incoming", "hedda", "knows"],
    ]);
  });

  it("skips links whose other end is not in the world", () => {
    const w = world({ entities: [entity("mara", "character")], links: [link("mara", "gone", "knows")] });
    expect(relationsOf(w, "mara")).toEqual([]);
  });
});

describe("entityTraits", () => {
  it("shows where a character is and its conditions", () => {
    const w = world({
      entities: [
        entity("mara", "character", {
          conditions: [
            { name: "Erschöpft", description: "" },
            { name: "Benommen", description: "" },
          ],
        }),
        entity("krug", "location", { label: "Gasthaus Zum Krug" }),
      ],
      links: [link("mara", "krug", "located_in")],
    });
    expect(entityTraits(w, w.entities[0])).toEqual([{ text: "Gasthaus Zum Krug" }, { text: "Erschöpft, Benommen" }]);
  });

  it("falls back to an unknown whereabouts note for a character without location or conditions", () => {
    const w = world({ entities: [entity("graf", "character")] });
    expect(entityTraits(w, w.entities[0])).toEqual([{ key: "play.world.traits.whereaboutsUnknown" }]);
  });

  it("counts who is at a location", () => {
    const w = world({
      entities: [entity("krug", "location"), entity("mara", "character"), entity("hedda", "character")],
      links: [link("mara", "krug", "located_in"), link("hedda", "krug", "located_in")],
    });
    expect(entityTraits(w, w.entities[0])).toEqual([{ key: "play.world.traits.presentCount", params: { count: 2 } }]);
  });

  it("names the container of an empty location", () => {
    const w = world({
      entities: [entity("krypta", "location"), entity("kapelle", "location", { label: "Kapelle" })],
      links: [link("kapelle", "krypta", "contains")],
    });
    expect(entityTraits(w, w.entities[0])).toEqual([{ key: "play.world.traits.inside", params: { name: "Kapelle" } }]);
  });

  it("names the owner of an item before its container", () => {
    const w = world({
      entities: [
        entity("schluessel", "item"),
        entity("aldric", "character", { label: "Bruder Aldric" }),
        entity("kapelle", "location", { label: "Kapelle" }),
      ],
      links: [link("kapelle", "schluessel", "contains"), link("aldric", "schluessel", "possesses")],
    });
    expect(entityTraits(w, w.entities[0])).toEqual([{ key: "play.world.traits.heldBy", params: { name: "Bruder Aldric" } }]);
  });

  it("shows the kind and first condition for creatures and factions", () => {
    const w = world({
      entities: [entity("wolf", "creature", { conditions: [{ name: "Hungrig", description: "" }] })],
    });
    expect(entityTraits(w, w.entities[0])).toEqual([{ key: "play.world.kind.creature" }, { text: "Hungrig" }]);
  });
});

describe("knowledge lookups", () => {
  const w = world({
    entities: [entity("mara", "character"), entity("hedda", "character"), entity("krug", "location")],
    facts: [fact("f1", "krug"), fact("f2"), fact("f3", "krug")],
    knowledge: [know("hedda", "f1", 1), know("mara", "f2", 5, 8), know("mara", "f1", 2), know("ghost", "f3", 1)],
  });

  it("lists an actor's entries known at the turn, ordered by learning turn", () => {
    expect(knowledgeOf(w, "mara", 9).map((e) => [e.entry.fact_id, e.status])).toEqual([
      ["f1", "known"],
      ["f2", "forgotten"],
    ]);
    expect(knowledgeOf(w, "mara", 3).map((e) => e.entry.fact_id)).toEqual(["f1"]);
  });

  it("lists who knows a fact at the turn, skipping actors missing from the world", () => {
    expect(knowersOf(w, "f1", 1).map((k) => k.actor.id)).toEqual(["hedda"]);
    expect(knowersOf(w, "f1", 2).map((k) => k.actor.id)).toEqual(["hedda", "mara"]);
    expect(knowersOf(w, "f3", 5)).toEqual([]);
  });

  it("finds the facts about an entity", () => {
    expect(factsAbout(w, "krug").map((f) => f.id)).toEqual(["f1", "f3"]);
  });

  it("lists the actors that have any knowledge, in world order", () => {
    expect(actorsWithKnowledge(w).map((a) => a.id)).toEqual(["mara", "hedda"]);
  });
});
