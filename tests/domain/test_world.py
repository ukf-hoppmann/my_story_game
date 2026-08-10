from __future__ import annotations

import pytest

from story_game.domain import (
    ActorProfile,
    ActorRole,
    EntityKind,
    EntityLink,
    Fact,
    InvalidReferenceError,
    KnowledgeEntry,
    RelationKind,
    StableId,
    StorySequence,
    ValidationError,
    WorldEntity,
    WorldRule,
    WorldState,
)


def sid(value: str) -> StableId:
    return StableId(value)


def test_inventory_and_location_are_derived_from_typed_links() -> None:
    mara = WorldEntity(
        sid("mara"),
        EntityKind.CHARACTER,
        "Mara",
        actor=ActorProfile(ActorRole.PLAYER),
    )
    harbor = WorldEntity(sid("harbor"), EntityKind.LOCATION, "Alter Hafen")
    key = WorldEntity(sid("key"), EntityKind.ITEM, "Messingschlüssel")
    world = WorldState(
        entities=(mara, harbor, key),
        links=(
            EntityLink(sid("mara-location"), mara.id, harbor.id, RelationKind.LOCATED_IN),
            EntityLink(sid("mara-key"), mara.id, key.id, RelationKind.POSSESSES),
        ),
    )

    assert world.location_of(mara.id) == harbor.id
    assert tuple(item.id for item in world.inventory(mara.id)) == (key.id,)


def test_world_rejects_relationships_to_unknown_entities() -> None:
    mara = WorldEntity(
        sid("mara"),
        EntityKind.CHARACTER,
        "Mara",
        actor=ActorProfile(ActorRole.PLAYER),
    )

    with pytest.raises(InvalidReferenceError):
        WorldState(
            entities=(mara,),
            links=(
                EntityLink(
                    sid("missing-location"),
                    mara.id,
                    sid("unknown"),
                    RelationKind.LOCATED_IN,
                ),
            ),
        )


def test_knowledge_requires_a_real_actor_and_fact() -> None:
    mara = WorldEntity(
        sid("mara"),
        EntityKind.CHARACTER,
        "Mara",
        actor=ActorProfile(ActorRole.PLAYER),
    )
    fact = Fact(
        sid("hidden-door"),
        "Hinter dem Hafenlager befindet sich eine verborgene Tür.",
    )

    world = WorldState(
        entities=(mara,),
        facts=(fact,),
        knowledge=(KnowledgeEntry(mara.id, fact.id, StorySequence(1)),),
    )

    assert world.fact(fact.id) == fact

    with pytest.raises(InvalidReferenceError):
        WorldState(
            entities=(mara,),
            facts=(fact,),
            knowledge=(KnowledgeEntry(sid("unknown-actor"), fact.id, StorySequence(1)),),
        )


def test_canonical_facts_and_rules_do_not_require_evidence() -> None:
    fact = Fact(sid("door"), "Die Tür ist verschlossen.")
    rule = WorldRule(sid("silver"), "Silber verletzt Geister.")

    world = WorldState(facts=(fact,), rules=(rule,))

    assert world.facts == (fact,)
    assert world.rules == (rule,)
    assert not hasattr(fact, "evidence")
    assert not hasattr(rule, "evidence")


def test_self_links_and_non_positive_quantities_are_rejected() -> None:
    entity_id = sid("item")
    with pytest.raises(ValidationError):
        EntityLink(entity_id, entity_id, entity_id, RelationKind.RELATED_TO)

    with pytest.raises(ValidationError):
        EntityLink(
            sid("invalid-quantity"),
            sid("owner"),
            sid("item"),
            RelationKind.POSSESSES,
            quantity=0,
        )
