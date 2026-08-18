"""Add the knowledge that belongs to the entities already selected."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.contracts import OperationResult, Success
from story_game.application.story_turn_context_errors import ContextSelectionError
from story_game.application.story_turn_context_models import (
    EntityCandidate,
    ReferencedData,
    SelectionPriority,
)
from story_game.domain import Goal, StableId, WorldState


@dataclass(frozen=True, slots=True)
class SelectReferencedFactsKnowledgeGoalsRequest:
    world: WorldState
    selected: tuple[EntityCandidate, ...]
    always_goals: tuple[Goal, ...]


class SelectReferencedFactsKnowledgeGoals:
    """Collect facts, actor knowledge and goals tied to the selected entities.

    Visibility is deliberately not a filter here. A ``director_only`` fact is
    selected like any other, because the model has to be able to steer towards
    something the player does not know yet. Deciding what the prose may reveal
    is a prompting concern, and hiding it from a UI is a separate read path.
    """

    def apply(
        self, request: SelectReferencedFactsKnowledgeGoalsRequest
    ) -> OperationResult[ReferencedData, ContextSelectionError]:
        world = request.world
        selected_ids = {candidate.entity_id for candidate in request.selected}

        facts = tuple(
            fact
            for fact in world.facts
            if fact.subject_id is None or fact.subject_id in selected_ids
        )
        fact_ids = {fact.id for fact in facts}
        knowledge = tuple(
            entry
            for entry in world.knowledge
            if entry.actor_id in selected_ids and entry.fact_id in fact_ids
        )

        always_ids = {goal.id for goal in request.always_goals}
        referenced = tuple(
            goal
            for goal in world.goals
            if goal.id not in always_ids
            and not selected_ids.isdisjoint(goal.related_entity_ids)
        )
        goals = (*request.always_goals, *referenced)

        closure: dict[StableId, EntityCandidate] = {}
        for goal, priority in (
            *(
                (goal, SelectionPriority.ALWAYS)
                for goal in request.always_goals
            ),
            *((goal, SelectionPriority.ONE_HOP) for goal in referenced),
        ):
            for entity_id in goal.related_entity_ids:
                if entity_id in selected_ids:
                    continue
                current = closure.get(entity_id)
                if current is not None and current.priority <= priority:
                    continue
                closure[entity_id] = EntityCandidate(
                    entity_id,
                    priority,
                    f"Ziel {goal.title!r}",
                )

        return Success(
            ReferencedData(
                facts=facts,
                knowledge=knowledge,
                goals=goals,
                closure_candidates=tuple(closure.values()),
            )
        )
