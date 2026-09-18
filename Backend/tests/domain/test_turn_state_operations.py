from __future__ import annotations

import pytest

from story_game.domain import (
    ActorProfile,
    ActorRole,
    ApprovedChangeSet,
    EntityKind,
    Fact,
    GameConfiguration,
    GameState,
    InvalidReferenceError,
    KnowledgeEntry,
    PromptProfile,
    RemoveFact,
    SetSceneLocations,
    StateRevision,
    StorySequence,
    StoryState,
    ValidationError,
    WorldEntity,
    WorldState,
)
from tests.ids import sid


MAREN = sid("maren")
TAVERN = sid("tavern")
FOREST = sid("forest")
SECRET = sid("f-secret")


def world() -> WorldState:
    return WorldState(
        entities=(
            WorldEntity(
                MAREN,
                EntityKind.CHARACTER,
                "Maren",
                actor=ActorProfile(ActorRole.PLAYER),
            ),
            WorldEntity(TAVERN, EntityKind.LOCATION, "Wirtshaus"),
            WorldEntity(FOREST, EntityKind.LOCATION, "Schwarzwald"),
        ),
        facts=(
            Fact(SECRET, "Die Tür ist verschlossen."),
            Fact(sid("f-other"), "Es regnet."),
        ),
        knowledge=(KnowledgeEntry(MAREN, SECRET, StorySequence(1)),),
        scene_location_ids=(TAVERN,),
    )


def configuration() -> GameConfiguration:
    return GameConfiguration(
        language="de",
        prompt_profile=PromptProfile(
            genre="dark_fantasy",
            tone="balanced",
            prose_style="balanced",
            perspective="second_person",
            pacing="balanced",
            control_mode="player",
            player_agency="strict",
            consequence="balanced",
            challenge="balanced",
            content_profile="teen",
        ),
        narrative_boundaries=("Keine sexualisierte Gewalt",),
        prompt_package_id="story.base",
        prompt_package_version="1",
    )


def state() -> GameState:
    return GameState(
        sid("run"), StateRevision(1), configuration(), world(), StoryState()
    )


def apply(*operations) -> GameState:
    return state().apply(
        ApprovedChangeSet(sid("proposal"), StateRevision(1), operations)
    )


def test_the_scene_can_move_on_to_another_location() -> None:
    result = apply(SetSceneLocations((FOREST,)))

    assert result.world.scene_location_ids == (FOREST,)
    assert result.world.primary_scene_location() == FOREST


def test_the_scene_can_hold_several_ordered_locations() -> None:
    result = apply(SetSceneLocations((FOREST, TAVERN)))

    assert result.world.scene_location_ids == (FOREST, TAVERN)


def test_the_scene_can_be_cleared() -> None:
    result = apply(SetSceneLocations(()))

    assert result.world.scene_location_ids == ()
    assert result.world.primary_scene_location() is None


def test_the_scene_cannot_move_to_an_unknown_entity() -> None:
    with pytest.raises(InvalidReferenceError):
        apply(SetSceneLocations((sid("nowhere"),)))


def test_the_scene_cannot_move_to_something_that_is_not_a_location() -> None:
    with pytest.raises(ValidationError):
        apply(SetSceneLocations((MAREN,)))


def test_a_fact_that_no_longer_holds_can_be_removed() -> None:
    result = apply(RemoveFact(sid("f-other")))

    assert [fact.id for fact in result.world.facts] == [SECRET]


def test_removing_a_fact_takes_the_knowledge_about_it_along() -> None:
    """An actor cannot keep knowing a fact the world no longer contains."""
    result = apply(RemoveFact(SECRET))

    assert [fact.id for fact in result.world.facts] == [sid("f-other")]
    assert result.world.knowledge == ()


def test_removing_an_unknown_fact_is_rejected() -> None:
    with pytest.raises(InvalidReferenceError):
        apply(RemoveFact(sid("never-existed")))


def test_both_operations_advance_the_revision_like_any_other_change() -> None:
    result = apply(SetSceneLocations((FOREST,)), RemoveFact(SECRET))

    assert result.revision == StateRevision(2)
    assert result.world.scene_location_ids == (FOREST,)
    assert result.world.knowledge == ()
