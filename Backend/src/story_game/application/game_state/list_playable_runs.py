"""List the runs (templates and active playthroughs) one identity can play."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.game_models import RunSummary
from story_game.application.ports import GameStateStoreError, PlayableRunLister

from .error_mapping import map_game_state_error
from .errors import GameStateOperationError


@dataclass(frozen=True, slots=True)
class ListPlayableRunsRequest:
    issuer: str
    subject: str


class ListPlayableRuns:
    def __init__(self, lister: PlayableRunLister) -> None:
        self.lister = lister

    def apply(
        self, request: ListPlayableRunsRequest
    ) -> OperationResult[tuple[RunSummary, ...], GameStateOperationError]:
        try:
            summaries = self.lister.list_for_member(request.issuer, request.subject)
        except GameStateStoreError as error:
            return Failure(map_game_state_error(error))
        return Success(summaries)
