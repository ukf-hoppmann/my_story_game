from __future__ import annotations

import pytest

from story_game.domain import (
    ActorProfile,
    ActorRole,
    EntityKind,
    EntityLink,
    InvalidReferenceError,
    RelationKind,
    ValidationError,
    WorldEntity,
    WorldState,
)
from tests.ids import sid


def _tavern() -> WorldEntity:
    return WorldEntity(sid("tavern"), EntityKind.LOCATION, "Wirtshaus")


def _forest() -> WorldEntity:
    return WorldEntity(sid("forest"), EntityKind.LOCATION, "Schwarzwald")


def _maren() -> WorldEntity:
    return WorldEntity(
        sid("maren"),
        EntityKind.CHARACTER,
        "Maren",
        actor=ActorProfile(ActorRole.PLAYER),
    )


def test_scene_defaults_to_empty_and_has_no_primary_location() -> None:
    world = WorldState(entities=(_tavern(),))

    assert world.scene_location_ids == ()
    assert world.primary_scene_location() is None


def test_scene_keeps_its_order_and_reports_the_first_location_as_primary() -> None:
    tavern, forest = _tavern(), _forest()

    world = WorldState(
        entities=(tavern, forest),
        scene_location_ids=(forest.id, tavern.id),
    )

    assert world.scene_location_ids == (forest.id, tavern.id)
    assert world.primary_scene_location() == forest.id


def test_scene_is_independent_from_where_entities_are_located() -> None:
    """Director control may narrate a scene the controlled character is not in."""
    maren, tavern, forest = _maren(), _tavern(), _forest()

    world = WorldState(
        entities=(maren, tavern, forest),
        links=(
            EntityLink(sid("maren-at-tavern"), maren.id, tavern.id, RelationKind.LOCATED_IN),
        ),
        scene_location_ids=(forest.id,),
    )

    assert world.location_of(maren.id) == tavern.id
    assert world.primary_scene_location() == forest.id


def test_scene_rejects_an_unknown_location() -> None:
    with pytest.raises(InvalidReferenceError):
        WorldState(entities=(_tavern(),), scene_location_ids=(sid("unknown"),))


def test_scene_rejects_an_entity_that_is_not_a_location() -> None:
    maren = _maren()

    with pytest.raises(ValidationError):
        WorldState(entities=(maren,), scene_location_ids=(maren.id,))


def test_scene_rejects_duplicate_locations() -> None:
    tavern = _tavern()

    with pytest.raises(ValidationError):
        WorldState(entities=(tavern,), scene_location_ids=(tavern.id, tavern.id))
