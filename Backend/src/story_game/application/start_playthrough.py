"""Fork a DRAFT game run into a new, independent ACTIVE playthrough.

``GameState.run_id`` is the only run-scoped field on the canonical snapshot
(entities, links, facts, and goals underneath are plain data), so forking is
a structural copy: build a new ``GameRun`` at revision 1 and reuse the source
``GameState`` with its ``run_id``/``revision`` swapped. The source DRAFT is
never written to, so it stays available to fork again for another
independent playthrough of the same opening scenario.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TypeAlias

from story_game.application.contracts import Failure, OperationResult
from story_game.application.diagnostics import DiagnosticsLog, NullDiagnosticsLog
from story_game.application.game_models import LoadedGame
from story_game.application.game_state import (
    CreateGameRun,
    CreateGameRunRequest,
    LoadGame,
    LoadGameRequest,
)
from story_game.application.game_state.errors import GameStateOperationError
from story_game.application.run_initiator import RunInitiator
from story_game.application.start_playthrough_errors import (
    PlaythroughError,
    PlaythroughErrorKind,
)
from story_game.domain import (
    GameRole,
    GameRun,
    GameRunMember,
    GameRunStatus,
    StableId,
    StateRevision,
)

StartPlaythroughError: TypeAlias = PlaythroughError | GameStateOperationError


@dataclass(frozen=True, slots=True)
class StartPlaythroughRequest:
    """Which DRAFT to fork, and who becomes the new playthrough's owner."""

    source_run_id: StableId
    initiator: RunInitiator


class StartPlaythrough:
    """Fork a DRAFT template into a new, independently playable ACTIVE run."""

    def __init__(
        self,
        load_game: LoadGame,
        game_run_creator: CreateGameRun,
        *,
        new_id: Callable[[], StableId] = StableId.new,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        diagnostics: DiagnosticsLog = NullDiagnosticsLog(),
    ) -> None:
        self._load_game = load_game
        self._game_run_creator = game_run_creator
        self._new_id = new_id
        self._now = now
        self._diagnostics = diagnostics

    def apply(
        self, request: StartPlaythroughRequest
    ) -> OperationResult[LoadedGame, StartPlaythroughError]:
        self._diagnostics.trace(
            "start_playthrough.start", source_run_id=str(request.source_run_id)
        )
        loaded = self._load_game.apply(
            LoadGameRequest(
                request.source_run_id,
                request.initiator.issuer,
                request.initiator.subject,
            )
        )
        if isinstance(loaded, Failure):
            return loaded
        source_run, source_state = loaded.data.run, loaded.data.state

        if source_run.status is not GameRunStatus.DRAFT:
            return Failure(
                PlaythroughError(
                    PlaythroughErrorKind.SOURCE_NOT_DRAFT,
                    "Nur eine Vorlage im Status DRAFT kann als neues Spiel "
                    "abgezweigt werden.",
                )
            )

        controlled_entity_ids = next(
            (member.controlled_entity_ids for member in source_run.members), ()
        )
        run_id = self._new_id()
        timestamp = self._now()
        run = GameRun(
            id=run_id,
            name=source_run.name,
            status=GameRunStatus.ACTIVE,
            current_revision=StateRevision(1),
            members=(
                GameRunMember(
                    issuer=request.initiator.issuer,
                    subject=request.initiator.subject,
                    game_role=GameRole.OWNER,
                    controlled_entity_ids=controlled_entity_ids,
                ),
            ),
            created_at=timestamp,
            updated_at=timestamp,
        )
        state = replace(source_state, run_id=run_id, revision=StateRevision(1))

        created = self._game_run_creator.apply(CreateGameRunRequest(run, state))
        self._diagnostics.trace(
            "start_playthrough.done",
            source_run_id=str(request.source_run_id),
            run_id=str(run_id),
            success=not isinstance(created, Failure),
        )
        return created


__all__ = [
    "StartPlaythrough",
    "StartPlaythroughError",
    "StartPlaythroughRequest",
]
