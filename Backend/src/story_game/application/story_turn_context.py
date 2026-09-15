"""Select the explainable slice of the game state one story turn needs."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.apply_selection_budget import (
    ApplySelectionBudget,
    ApplySelectionBudgetRequest,
)
from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.diagnostics import DiagnosticsLog, NullDiagnosticsLog
from story_game.application.expand_one_hop import ExpandOneHop, ExpandOneHopRequest
from story_game.application.populate_scene_locations import (
    PopulateSceneLocations,
    PopulateSceneLocationsRequest,
)
from story_game.application.resolve_mentioned_entities import (
    ResolveMentionedEntities,
    ResolveMentionedEntitiesRequest,
)
from story_game.application.select_always_included import (
    SelectAlwaysIncluded,
    SelectAlwaysIncludedRequest,
)
from story_game.application.select_referenced_facts_knowledge_goals import (
    SelectReferencedFactsKnowledgeGoals,
    SelectReferencedFactsKnowledgeGoalsRequest,
)
from story_game.application.story_turn_context_errors import ContextSelectionError
from story_game.application.story_turn_context_models import (
    SelectedStoryTurnContext,
    SelectionBudget,
    merge_candidates,
)
from story_game.domain import GameState, StableId, StoryState


@dataclass(frozen=True, slots=True)
class SelectStoryTurnContextRequest:
    """Everything one turn's context selection reads, already loaded."""

    game_state: GameState
    controlled_entity_ids: tuple[StableId, ...]
    player_input: str


class SelectStoryTurnContext:
    """Compose the six deterministic selection steps in a visible order.

    Runs no model call, writes nothing and leaves the given ``GameState``
    untouched. Which of the selected information the prose may actually reveal
    is decided later, when the request is rendered.
    """

    def __init__(
        self,
        always_included: SelectAlwaysIncluded,
        mentioned_entities: ResolveMentionedEntities,
        scene_locations: PopulateSceneLocations,
        one_hop: ExpandOneHop,
        referenced_data: SelectReferencedFactsKnowledgeGoals,
        selection_budget: ApplySelectionBudget,
        budget: SelectionBudget = SelectionBudget(),
        diagnostics: DiagnosticsLog = NullDiagnosticsLog(),
    ) -> None:
        self._always_included = always_included
        self._mentioned_entities = mentioned_entities
        self._scene_locations = scene_locations
        self._one_hop = one_hop
        self._referenced_data = referenced_data
        self._selection_budget = selection_budget
        self._budget = budget
        self._diagnostics = diagnostics

    def apply(
        self, request: SelectStoryTurnContextRequest
    ) -> OperationResult[SelectedStoryTurnContext, ContextSelectionError]:
        world = request.game_state.world
        self._diagnostics.trace(
            "select_story_turn_context.request",
            player_input=request.player_input,
            controlled_entity_ids=[str(entity_id) for entity_id in request.controlled_entity_ids],
        )

        frame = self._always_included.apply(
            SelectAlwaysIncludedRequest(
                request.game_state, request.controlled_entity_ids, self._budget
            )
        )
        if isinstance(frame, Failure):
            return frame

        mentioned = self._mentioned_entities.apply(
            ResolveMentionedEntitiesRequest(
                world,
                request.player_input,
                _latest_prose(request.game_state.story),
            )
        )
        if isinstance(mentioned, Failure):
            return mentioned

        scene = self._scene_locations.apply(
            PopulateSceneLocationsRequest(world, mentioned.data)
        )
        if isinstance(scene, Failure):
            return scene

        selected = merge_candidates(
            frame.data.candidates, scene.data.candidates, mentioned.data
        )

        hop = self._one_hop.apply(ExpandOneHopRequest(world, selected))
        if isinstance(hop, Failure):
            return hop
        selected = merge_candidates(selected, hop.data)

        referenced = self._referenced_data.apply(
            SelectReferencedFactsKnowledgeGoalsRequest(
                world, selected, frame.data.main_goals
            )
        )
        if isinstance(referenced, Failure):
            return referenced
        selected = merge_candidates(selected, referenced.data.closure_candidates)

        budgeted = self._selection_budget.apply(
            ApplySelectionBudgetRequest(
                world,
                selected,
                referenced.data.facts,
                referenced.data.knowledge,
                referenced.data.goals,
                self._budget,
            )
        )
        if isinstance(budgeted, Failure):
            return budgeted

        kept = {entity.id for entity in budgeted.data.entities}
        selected_context = SelectedStoryTurnContext(
            summaries=frame.data.summaries,
            recent_turns=frame.data.recent_turns,
            controlled_entities=frame.data.controlled_entities,
            scene_locations=tuple(
                location
                for location in scene.data.scene_locations
                if location.id in kept
            ),
            entities=budgeted.data.entities,
            links=budgeted.data.links,
            facts=budgeted.data.facts,
            knowledge=budgeted.data.knowledge,
            rules=frame.data.rules,
            goals=budgeted.data.goals,
            language=frame.data.language,
            perspective=frame.data.perspective,
            control_mode=frame.data.control_mode,
            narrative_boundaries=frame.data.narrative_boundaries,
            selection_reasons=budgeted.data.reasons,
            truncated=budgeted.data.truncated,
        )
        self._diagnostics.trace(
            "select_story_turn_context.result",
            entity_count=len(selected_context.entities),
            fact_count=len(selected_context.facts),
            truncated=selected_context.truncated,
            selection_reasons=selected_context.selection_reasons,
        )
        return Success(selected_context)


def build_story_turn_context_selection(
    budget: SelectionBudget = SelectionBudget(),
    diagnostics: DiagnosticsLog = NullDiagnosticsLog(),
) -> SelectStoryTurnContext:
    """Wire the default selection so callers need not know its six steps."""
    return SelectStoryTurnContext(
        SelectAlwaysIncluded(),
        ResolveMentionedEntities(),
        PopulateSceneLocations(),
        ExpandOneHop(),
        SelectReferencedFactsKnowledgeGoals(),
        ApplySelectionBudget(),
        budget,
        diagnostics,
    )


def _latest_prose(story: StoryState) -> str:
    """The most recent narration, or the opening while no turn exists yet."""
    if story.turns:
        return story.turns[-1].narration
    return story.initialization.narration if story.initialization else ""
