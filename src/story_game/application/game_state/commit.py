"""Commit application-approved changes to one canonical run."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.ports import GameStateStoreError, GameStateWriter
from story_game.domain import ApprovedChangeSet, DomainError, GameState, StableId

from .error_mapping import map_game_state_error
from .errors import GameStateOperationError


@dataclass(frozen=True, slots=True)
class CommitGameStateRequest:
    run_id: StableId
    changes: ApprovedChangeSet


class CommitGameStateChanges:
    """Atomically apply an approved change set to one canonical run."""

    def __init__(self, writer: GameStateWriter) -> None:
        self._writer = writer

    def apply(
        self, request: CommitGameStateRequest
    ) -> OperationResult[GameState, GameStateOperationError]:
        try:
            state = self._writer.commit(request.run_id, request.changes)
        except (GameStateStoreError, DomainError) as error:
            return Failure(map_game_state_error(error))
        return Success(state)
