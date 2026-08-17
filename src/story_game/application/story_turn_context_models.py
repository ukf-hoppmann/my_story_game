"""Shared values for the deterministic story-turn context selection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from story_game.domain import (
    EntityLink,
    Fact,
    Goal,
    KnowledgeEntry,
    StableId,
    StorySummary,
    StoryTurn,
    WorldEntity,
    WorldRule,
)


class SelectionPriority(IntEnum):
    """Why an entity was selected, ordered from most to least important.

    The order decides who survives a tight budget. Lower is more important.
    """

    ALWAYS = 0
    """Part of the frame of every turn and never dropped by the budget."""

    PRIMARY_SCENE = 1
    """Present at a location the world itself names as the current scene."""

    PLAYER_INPUT = 2
    """Named in the current player input."""

    RECENT_PROSE = 3
    """Named in the most recent narration."""

    SECONDARY_SCENE = 4
    """Present at a location mentioned in the text but not part of the scene."""

    ONE_HOP = 5
    """Directly related to something already selected."""


@dataclass(frozen=True, slots=True)
class EntityCandidate:
    """One selected entity with the reason it survived, for tests and debugging."""

    entity_id: StableId
    priority: SelectionPriority
    detail: str


@dataclass(frozen=True, slots=True)
class SelectionBudget:
    """Hard limits that keep one prompt from growing without bound.

    Counts only. A token budget needs rendered text and therefore belongs to the
    later request projection, not to this selection.
    """

    max_entities: int = 15
    max_facts: int = 20
    max_goals: int = 10
    recent_turn_count: int = 2

    def __post_init__(self) -> None:
        for name in ("max_entities", "max_facts", "max_goals"):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} muss positiv sein")
        if self.recent_turn_count < 0:
            raise ValueError("recent_turn_count darf nicht negativ sein")


@dataclass(frozen=True, slots=True)
class AlwaysIncludedContext:
    """The frame every turn carries regardless of what the text mentions."""

    summary: StorySummary | None
    recent_turns: tuple[StoryTurn, ...]
    rules: tuple[WorldRule, ...]
    main_goals: tuple[Goal, ...]
    controlled_entity: WorldEntity | None
    language: str
    perspective: str
    control_mode: str
    narrative_boundaries: tuple[str, ...]
    candidates: tuple[EntityCandidate, ...]


@dataclass(frozen=True, slots=True)
class ReferencedData:
    """Facts, knowledge and goals that belong to the selected entities."""

    facts: tuple[Fact, ...]
    knowledge: tuple[KnowledgeEntry, ...]
    goals: tuple[Goal, ...]
    closure_candidates: tuple[EntityCandidate, ...]


@dataclass(frozen=True, slots=True)
class BudgetedSelection:
    """The capped, referentially closed result of one selection."""

    entities: tuple[WorldEntity, ...]
    links: tuple[EntityLink, ...]
    facts: tuple[Fact, ...]
    knowledge: tuple[KnowledgeEntry, ...]
    goals: tuple[Goal, ...]
    reasons: tuple[EntityCandidate, ...]
    truncated: bool


@dataclass(frozen=True, slots=True)
class SelectedStoryTurnContext:
    """One explainable slice of the game state prepared for a story turn.

    Holds complete domain values, never partially populated copies. It is a
    prompt slice, not a view: it deliberately does not filter by ``Visibility``,
    because the model has to be able to work towards facts the player does not
    know yet. A UI that shows what somebody knows must filter the ``WorldState``
    itself.
    """

    summary: StorySummary | None
    recent_turns: tuple[StoryTurn, ...]
    controlled_entity: WorldEntity | None
    scene_locations: tuple[WorldEntity, ...]
    entities: tuple[WorldEntity, ...]
    links: tuple[EntityLink, ...]
    facts: tuple[Fact, ...]
    knowledge: tuple[KnowledgeEntry, ...]
    rules: tuple[WorldRule, ...]
    goals: tuple[Goal, ...]
    language: str
    perspective: str
    control_mode: str
    narrative_boundaries: tuple[str, ...]
    selection_reasons: tuple[EntityCandidate, ...]
    truncated: bool


def merge_candidates(
    *groups: tuple[EntityCandidate, ...],
) -> tuple[EntityCandidate, ...]:
    """Keep the most important reason per entity, in first-seen order."""
    best: dict[StableId, EntityCandidate] = {}
    for group in groups:
        for candidate in group:
            current = best.get(candidate.entity_id)
            if current is None or candidate.priority < current.priority:
                best[candidate.entity_id] = candidate
    return tuple(best.values())
