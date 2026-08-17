from __future__ import annotations

from story_game.application import Success
from story_game.application.populate_scene_locations import (
    PopulateSceneLocations,
    PopulateSceneLocationsRequest,
)
from story_game.application.story_turn_context_models import (
    EntityCandidate,
    SelectionPriority,
)
from tests.application import turn_context_world as w


def populate(scene, mentioned=()):
    result = PopulateSceneLocations().apply(
        PopulateSceneLocationsRequest(
            w.world(scene),
            tuple(
                EntityCandidate(item, SelectionPriority.PLAYER_INPUT, "test")
                for item in mentioned
            ),
        )
    )
    assert isinstance(result, Success)
    return result.data


def priorities(data) -> dict:
    return {item.entity_id: item.priority for item in data.candidates}


def test_the_scene_pointer_brings_its_location_and_everyone_there() -> None:
    found = priorities(populate((w.TAVERN,)))

    assert found[w.TAVERN] is SelectionPriority.PRIMARY_SCENE
    assert found[w.MAREN] is SelectionPriority.PRIMARY_SCENE
    assert found[w.WIRT] is SelectionPriority.PRIMARY_SCENE
    assert w.ALMA not in found
    assert w.BRUDER not in found


def test_the_scene_works_without_anything_being_named_in_the_text() -> None:
    """'Maren geht weiter' names no place — the world still knows the scene."""
    found = priorities(populate((w.TAVERN,), mentioned=()))

    assert w.TAVERN in found
    assert data_locations(populate((w.TAVERN,))) == (w.TAVERN,)


def test_several_scene_locations_keep_their_order() -> None:
    data = populate((w.FOREST, w.TAVERN))

    assert data_locations(data) == (w.FOREST, w.TAVERN)
    found = priorities(data)
    assert found[w.ALMA] is SelectionPriority.PRIMARY_SCENE
    assert found[w.WIRT] is SelectionPriority.PRIMARY_SCENE


def test_a_location_only_mentioned_in_the_text_stays_secondary() -> None:
    found = priorities(populate((w.TAVERN,), mentioned=(w.CAPITAL,)))

    assert found[w.TAVERN] is SelectionPriority.PRIMARY_SCENE
    assert found[w.CAPITAL] is SelectionPriority.SECONDARY_SCENE
    assert found[w.BRUDER] is SelectionPriority.SECONDARY_SCENE


def test_a_mentioned_location_that_is_already_the_scene_stays_primary() -> None:
    found = priorities(populate((w.TAVERN,), mentioned=(w.TAVERN,)))

    assert found[w.TAVERN] is SelectionPriority.PRIMARY_SCENE


def test_mentioned_non_locations_do_not_populate_anything() -> None:
    found = priorities(populate((), mentioned=(w.ALMA,)))

    assert found == {}


def test_an_empty_scene_pointer_yields_no_primary_locations() -> None:
    data = populate(())

    assert data_locations(data) == ()
    assert data.candidates == ()


def data_locations(data) -> tuple:
    return tuple(location.id for location in data.scene_locations)
