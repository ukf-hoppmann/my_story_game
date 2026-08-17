"""Select the frame every story turn carries, regardless of its text."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.story_turn_context_errors import (
    ContextSelectionError,
    ContextSelectionErrorKind,
)
from story_game.application.story_turn_context_models import (
    AlwaysIncludedContext,
    EntityCandidate,
    SelectionBudget,
    SelectionPriority,
)
from story_game.domain import (
    GameState,
    GoalKind,
    GoalStatus,
    InvalidReferenceError,
    StableId,
)


@dataclass(frozen=True, slots=True)
class SelectAlwaysIncludedRequest:
    game_state: GameState
    controlled_entity_id: StableId | None
    budget: SelectionBudget


class SelectAlwaysIncluded:
    """Collect the values a turn needs even when the text mentions nothing."""

    def apply(
        self, request: SelectAlwaysIncludedRequest
    ) -> OperationResult[AlwaysIncludedContext, ContextSelectionError]:
        state = request.game_state
        controlled = None
        candidates: tuple[EntityCandidate, ...] = ()
        if request.controlled_entity_id is not None:
            try:
                controlled = state.world.entity(request.controlled_entity_id)
            except InvalidReferenceError:
                return Failure(
                    ContextSelectionError(
                        ContextSelectionErrorKind.UNKNOWN_CONTROLLED_ENTITY,
                        "Die gesteuerte Figur gehört nicht zu dieser Revision.",
                    )
                )
            candidates = (
                EntityCandidate(
                    controlled.id,
                    SelectionPriority.ALWAYS,
                    "gesteuerte Figur",
                ),
            )

        turns = state.story.turns
        recent = (
            turns[-request.budget.recent_turn_count :]
            if request.budget.recent_turn_count
            else ()
        )
        profile = state.configuration.prompt_profile
        return Success(
            AlwaysIncludedContext(
                summary=state.story.summary,
                recent_turns=tuple(recent),
                rules=state.world.rules,
                main_goals=tuple(
                    goal
                    for goal in state.world.goals
                    if goal.kind is GoalKind.MAIN and goal.status is GoalStatus.OPEN
                ),
                controlled_entity=controlled,
                language=state.configuration.language,
                perspective=profile.perspective,
                control_mode=profile.control_mode,
                narrative_boundaries=state.configuration.narrative_boundaries,
                candidates=candidates,
            )
        )
