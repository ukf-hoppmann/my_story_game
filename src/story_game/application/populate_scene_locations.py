"""Turn the named places of a turn into the cast actually present there."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.contracts import OperationResult, Success
from story_game.application.story_turn_context_errors import ContextSelectionError
from story_game.application.story_turn_context_models import (
    EntityCandidate,
    SelectionPriority,
)
from story_game.domain import (
    EntityKind,
    RelationKind,
    StableId,
    WorldEntity,
    WorldState,
)


@dataclass(frozen=True, slots=True)
class PopulateSceneLocationsRequest:
    world: WorldState
    mentioned: tuple[EntityCandidate, ...]


@dataclass(frozen=True, slots=True)
class ScenePopulation:
    scene_locations: tuple[WorldEntity, ...]
    candidates: tuple[EntityCandidate, ...]


class PopulateSceneLocations:
    """Fill the scene from the world's own scene pointer, then from the text.

    The pointer is the primary truth: it survives a turn whose prose names no
    place at all. Places merely mentioned in the text are secondary and never
    displace it.
    """

    def apply(
        self, request: PopulateSceneLocationsRequest
    ) -> OperationResult[ScenePopulation, ContextSelectionError]:
        world = request.world
        primary_ids = world.scene_location_ids
        secondary_ids = tuple(
            candidate.entity_id
            for candidate in request.mentioned
            if candidate.entity_id not in primary_ids
            and _is_location(world, candidate.entity_id)
        )

        candidates: list[EntityCandidate] = []
        for location_id in primary_ids:
            candidates.extend(
                _at_location(world, location_id, SelectionPriority.PRIMARY_SCENE)
            )
        for location_id in secondary_ids:
            candidates.extend(
                _at_location(world, location_id, SelectionPriority.SECONDARY_SCENE)
            )

        return Success(
            ScenePopulation(
                scene_locations=tuple(
                    world.entity(location_id) for location_id in primary_ids
                ),
                candidates=tuple(candidates),
            )
        )


def _is_location(world: WorldState, entity_id: StableId) -> bool:
    return any(
        entity.id == entity_id and entity.kind is EntityKind.LOCATION
        for entity in world.entities
    )


def _at_location(
    world: WorldState,
    location_id: StableId,
    priority: SelectionPriority,
) -> tuple[EntityCandidate, ...]:
    label = world.entity(location_id).label
    present = tuple(
        link.source_id
        for link in world.links
        if link.kind in {RelationKind.LOCATED_IN, RelationKind.CONTAINS}
        and link.target_id == location_id
    )
    return (
        EntityCandidate(location_id, priority, f"Schauplatz {label!r}"),
        *(
            EntityCandidate(entity_id, priority, f"befindet sich in {label!r}")
            for entity_id in present
        ),
    )
