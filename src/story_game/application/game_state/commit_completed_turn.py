"""Create and atomically persist one completed story turn."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.game_models import CompletedTurnPersistenceRequest
from story_game.application.ports import (
    CompletedTurnWriter,
    GameStateReader,
    GameStateStoreError,
)
from story_game.domain import (
    ApprovedChangeSet,
    DomainError,
    GameState,
    StableId,
    StorySequence,
    StorySummary,
    StoryTurn,
)

from .error_mapping import map_game_state_error
from .errors import GameStateOperationError


@dataclass(frozen=True, slots=True)
class CommitCompletedTurnRequest:
    run_id: StableId
    changes: ApprovedChangeSet
    turn_id: StableId
    player_input: str
    narration: str
    summary_text: str | None
    completed_at: datetime


class CommitCompletedTurn:
    def __init__(
        self,
        writer: CompletedTurnWriter,
        reader: GameStateReader,
    ) -> None:
        self.writer = writer
        self.reader = reader

    def apply(
        self, request: CommitCompletedTurnRequest
    ) -> OperationResult[GameState, GameStateOperationError]:
        try:
            current = self.reader.load_state(request.run_id)
            sequence = StorySequence(current.story.current_turn_sequence + 1)
            resulting_revision = request.changes.base_revision.next()
            turn = StoryTurn(
                request.turn_id,
                sequence,
                request.player_input,
                request.narration,
                request.changes.base_revision,
                resulting_revision,
                request.completed_at,
            )
            summary = (
                None
                if request.summary_text is None
                else StorySummary(sequence, request.summary_text, resulting_revision)
            )
            state = self.writer.commit_turn(
                CompletedTurnPersistenceRequest(
                    request.run_id, request.changes, turn, summary
                )
            )
        except (GameStateStoreError, DomainError) as error:
            return Failure(map_game_state_error(error))
        return Success(state)
