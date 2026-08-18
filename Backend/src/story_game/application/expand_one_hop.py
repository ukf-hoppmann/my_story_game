"""Add the immediate surroundings of everything already selected."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.contracts import OperationResult, Success
from story_game.application.story_turn_context_errors import ContextSelectionError
from story_game.application.story_turn_context_models import (
    EntityCandidate,
    SelectionPriority,
)
from story_game.domain import StableId, WorldState


@dataclass(frozen=True, slots=True)
class ExpandOneHopRequest:
    world: WorldState
    selected: tuple[EntityCandidate, ...]


class ExpandOneHop:
    """Follow every relation exactly one step, in both directions.

    One hop keeps the slice explainable and bounded. A wider radius is a
    separate decision, not a knob to turn here.
    """

    def apply(
        self, request: ExpandOneHopRequest
    ) -> OperationResult[tuple[EntityCandidate, ...], ContextSelectionError]:
        seeds = {candidate.entity_id for candidate in request.selected}
        reached: dict[StableId, EntityCandidate] = {}
        for link in request.world.links:
            for source_id, target_id in (
                (link.source_id, link.target_id),
                (link.target_id, link.source_id),
            ):
                if source_id not in seeds or target_id in seeds:
                    continue
                if target_id in reached:
                    continue
                reached[target_id] = EntityCandidate(
                    target_id,
                    SelectionPriority.ONE_HOP,
                    f"{link.kind.value} zu {_label(request.world, source_id)!r}",
                )
        return Success(tuple(reached.values()))


def _label(world: WorldState, entity_id: StableId) -> str:
    return world.entity(entity_id).label
