"""Application workflow for one complete story turn."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypeAlias

from story_game.application.approve_story_turn_changes import (
    ApproveStoryTurnChanges,
    ApproveStoryTurnChangesRequest,
)
from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.extract_story_turn_changes import (
    ExtractStoryTurnChanges,
    ExtractStoryTurnChangesRequest,
)
from story_game.application.game_state import (
    CommitCompletedTurn,
    CommitCompletedTurnRequest,
    LoadGame,
    LoadGameRequest,
)
from story_game.application.game_state.errors import GameStateOperationError
from story_game.application.generate_story import GenerateStory, GenerateStoryRequest
from story_game.application.initialize_game_run import RunInitiator
from story_game.application.story_turn_context import (
    SelectStoryTurnContext,
    SelectStoryTurnContextRequest,
)
from story_game.application.story_turn_context_errors import ContextSelectionError
from story_game.application.story_turn_errors import StoryTurnError, StoryTurnErrorKind
from story_game.domain import GameRun, GameState, StableId


StoryTurnWorkflowError: TypeAlias = (
    StoryTurnError | ContextSelectionError | GameStateOperationError
)


@dataclass(frozen=True, slots=True)
class PlayStoryTurnRequest:
    """What the player just did, in which run, as whom."""

    run_id: StableId
    initiator: RunInitiator
    player_input: str

    def __post_init__(self) -> None:
        player_input = self.player_input.strip()
        if not player_input:
            raise ValueError("Die Spielereingabe darf nicht leer sein")
        object.__setattr__(self, "player_input", player_input)


class PlayStoryTurn:
    """Load, select, narrate, extract, approve and commit one turn.

    The order is deliberately visible here rather than hidden in wiring. Both
    model calls happen outside the database transaction, so any failure before
    the commit simply leaves the previous revision standing.
    """

    def __init__(
        self,
        load_game: LoadGame,
        select_context: SelectStoryTurnContext,
        generate_story: GenerateStory,
        extract_changes: ExtractStoryTurnChanges,
        approve_changes: ApproveStoryTurnChanges,
        commit_turn: CommitCompletedTurn,
        *,
        new_id: Callable[[], StableId] = StableId.new,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._load_game = load_game
        self._select_context = select_context
        self._generate_story = generate_story
        self._extract_changes = extract_changes
        self._approve_changes = approve_changes
        self._commit_turn = commit_turn
        self._new_id = new_id
        self._now = now

    def apply(
        self, request: PlayStoryTurnRequest
    ) -> OperationResult[GameState, StoryTurnWorkflowError]:
        loaded = self._load_game.apply(LoadGameRequest(request.run_id))
        if isinstance(loaded, Failure):
            return loaded
        run, state = loaded.data.run, loaded.data.state

        controlled = _controlled_entity_id(run, request.initiator)
        if isinstance(controlled, Failure):
            return controlled

        context = self._select_context.apply(
            SelectStoryTurnContextRequest(state, controlled.data, request.player_input)
        )
        if isinstance(context, Failure):
            return context

        narrated = self._generate_story.apply(
            GenerateStoryRequest(
                context.data, state.configuration, request.player_input
            )
        )
        if isinstance(narrated, Failure):
            return narrated

        extracted = self._extract_changes.apply(
            ExtractStoryTurnChangesRequest(
                context.data, state.configuration, narrated.data.text
            )
        )
        if isinstance(extracted, Failure):
            return extracted

        approved = self._approve_changes.apply(
            ApproveStoryTurnChangesRequest(state, extracted.data)
        )
        if isinstance(approved, Failure):
            return approved

        return self._commit_turn.apply(
            CommitCompletedTurnRequest(
                run_id=request.run_id,
                changes=approved.data,
                turn_id=self._new_id(),
                player_input=request.player_input,
                narration=narrated.data.text,
                summary_text=None,
                completed_at=self._now(),
            )
        )


def _controlled_entity_id(
    run: GameRun, initiator: RunInitiator
) -> OperationResult[StableId | None, StoryTurnError]:
    """Find which figure the caller steers, if any.

    Director control binds no figure today, so ``None`` is a valid answer and
    not an error.
    """
    for member in run.members:
        if member.identity == (initiator.issuer, initiator.subject):
            return Success(member.player_entity_id)
    return Failure(
        StoryTurnError(
            StoryTurnErrorKind.UNKNOWN_MEMBER,
            "Die aufrufende Identität gehört nicht zu diesem GameRun.",
        )
    )
