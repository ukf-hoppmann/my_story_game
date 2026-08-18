"""Cap one selection without leaving dangling references behind."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.contracts import OperationResult, Success
from story_game.application.story_turn_context_errors import ContextSelectionError
from story_game.application.story_turn_context_models import (
    BudgetedSelection,
    EntityCandidate,
    SelectionBudget,
    SelectionPriority,
)
from story_game.domain import (
    Fact,
    Goal,
    KnowledgeEntry,
    StableId,
    WorldState,
)


@dataclass(frozen=True, slots=True)
class ApplySelectionBudgetRequest:
    world: WorldState
    candidates: tuple[EntityCandidate, ...]
    facts: tuple[Fact, ...]
    knowledge: tuple[KnowledgeEntry, ...]
    goals: tuple[Goal, ...]
    budget: SelectionBudget


class ApplySelectionBudget:
    """Keep the slice small while it stays internally consistent.

    Entities are ranked by why they were selected and, on a tie, by their stable
    order in the world so that the same input always yields the same slice.
    Whatever survives is then closed over: anything pointing at a dropped entity
    is dropped too, so the model never sees a reference it cannot resolve.

    Two things are kept even past the limit: the frame of every turn, and the
    locations the world itself names as the scene — without them a turn would no
    longer know where it takes place. Everyone standing in those locations stays
    budgeted, so a crowded place cannot crowd out the rest of the slice.
    """

    def apply(
        self, request: ApplySelectionBudgetRequest
    ) -> OperationResult[BudgetedSelection, ContextSelectionError]:
        world = request.world
        order = {entity.id: index for index, entity in enumerate(world.entities)}
        known = tuple(
            candidate
            for candidate in request.candidates
            if candidate.entity_id in order
        )
        ranked = sorted(
            known,
            key=lambda candidate: (candidate.priority, order[candidate.entity_id]),
        )

        scene_ids = set(world.scene_location_ids)
        keep_regardless = {
            item.entity_id
            for item in ranked
            if item.priority is SelectionPriority.ALWAYS or item.entity_id in scene_ids
        }
        required = [item for item in ranked if item.entity_id in keep_regardless]
        optional = [item for item in ranked if item.entity_id not in keep_regardless]
        room = max(request.budget.max_entities - len(required), 0)
        kept = [*required, *optional[:room]]
        truncated = len(kept) < len(ranked)

        selected: set[StableId] = {item.entity_id for item in kept}
        entities = tuple(
            entity for entity in world.entities if entity.id in selected
        )
        links = tuple(
            link
            for link in world.links
            if link.source_id in selected and link.target_id in selected
        )

        facts = tuple(
            fact
            for fact in request.facts
            if fact.subject_id is None or fact.subject_id in selected
        )
        if len(facts) > request.budget.max_facts:
            facts = facts[: request.budget.max_facts]
            truncated = True

        fact_ids = {fact.id for fact in facts}
        knowledge = tuple(
            entry
            for entry in request.knowledge
            if entry.actor_id in selected and entry.fact_id in fact_ids
        )

        goals = tuple(
            goal
            for goal in request.goals
            if set(goal.related_entity_ids) <= selected
        )
        if len(goals) > request.budget.max_goals:
            goals = goals[: request.budget.max_goals]
            truncated = True

        reasons = tuple(
            sorted(kept, key=lambda candidate: order[candidate.entity_id])
        )
        return Success(
            BudgetedSelection(
                entities=entities,
                links=links,
                facts=facts,
                knowledge=knowledge,
                goals=goals,
                reasons=reasons,
                truncated=truncated,
            )
        )
