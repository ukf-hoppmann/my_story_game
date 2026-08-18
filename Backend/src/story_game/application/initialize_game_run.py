"""Application workflow for creating and persisting the initial game state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypeAlias

from story_game.application.contracts import Failure, OperationResult
from story_game.application.diagnostics import DiagnosticsLog, NullDiagnosticsLog
from story_game.application.game_models import LoadedGame
from story_game.application.game_state import CreateGameRun, CreateGameRunRequest
from story_game.application.initialization_errors import StoryInitializationError
from story_game.application.initialization_models import (
    ControllableCharacterSeed,
    InitializedStory,
)
from story_game.application.initialize_story import InitializeStory, InitializeStoryRequest
from story_game.domain import (
    ActorRole,
    DomainError,
    GameRole,
    GameConfiguration,
    GameRun,
    GameRunMember,
    GameRunStatus,
    GameState,
    StableId,
    StateRevision,
)

from .game_state.errors import GameStateOperationError, StateRejected


InitialGameRunError: TypeAlias = StoryInitializationError | GameStateOperationError


def _required(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{label} darf nicht leer sein")
    return value


@dataclass(frozen=True, slots=True)
class RunInitiator:
    """External identity that owns the newly created game run."""

    issuer: str
    subject: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "issuer", _required(self.issuer, "Der Issuer"))
        object.__setattr__(self, "subject", _required(self.subject, "Das Subject"))


@dataclass(frozen=True, slots=True)
class InitializeGameRunRequest:
    """Caller input needed to create one initial DRAFT game run."""

    configuration: GameConfiguration
    run_name: str
    initial_prompt: str
    initiator: RunInitiator
    controllable_characters: tuple[ControllableCharacterSeed, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_name", _required(self.run_name, "Der Name"))
        object.__setattr__(
            self,
            "initial_prompt",
            _required(self.initial_prompt, "Der Initialprompt"),
        )


class InitializeGameRun:
    """Compose transient initialization with atomic revision-one persistence."""

    def __init__(
        self,
        story_initializer: InitializeStory,
        game_run_creator: CreateGameRun,
        *,
        new_id: Callable[[], StableId] = StableId.new,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        diagnostics: DiagnosticsLog = NullDiagnosticsLog(),
    ) -> None:
        self._story_initializer = story_initializer
        self._game_run_creator = game_run_creator
        self._new_id = new_id
        self._now = now
        self._diagnostics = diagnostics

    def apply(
        self, request: InitializeGameRunRequest
    ) -> OperationResult[LoadedGame, InitialGameRunError]:
        self._diagnostics.trace(
            "initialize_game_run.start", run_name=request.run_name
        )
        initialized = self._story_initializer.apply(
            InitializeStoryRequest(
                request.configuration,
                request.initial_prompt,
                request.controllable_characters,
            )
        )
        if isinstance(initialized, Failure):
            return initialized

        try:
            controlled_entity_ids = _controlled_entity_ids(
                initialized.data,
                request.configuration.prompt_profile.control_mode,
            )
            run_id = self._new_id()
            timestamp = self._now()
            run = GameRun(
                id=run_id,
                name=request.run_name,
                status=GameRunStatus.DRAFT,
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
            state = GameState(
                run_id=run_id,
                revision=StateRevision(1),
                configuration=request.configuration,
                world=initialized.data.world_state,
                story=initialized.data.story_state,
            )
        except (DomainError, ValueError) as error:
            return Failure(StateRejected(str(error)))

        created = self._game_run_creator.apply(CreateGameRunRequest(run, state))
        self._diagnostics.trace(
            "initialize_game_run.done",
            run_id=str(run_id),
            success=not isinstance(created, Failure),
        )
        return created


def _controlled_entity_ids(
    initialized: InitializedStory,
    control_mode: str,
) -> tuple[StableId, ...]:
    player_ids = tuple(
        entity.id
        for entity in initialized.world_state.entities
        if entity.actor is not None and entity.actor.role is ActorRole.PLAYER
    )
    if control_mode == "player":
        if len(player_ids) != 1:
            raise ValueError(
                "Der Player Mode benötigt genau einen Spielercharakter im WorldState"
            )
        return player_ids
    if control_mode == "director":
        return player_ids
    raise ValueError(f"Unbekannter Control Mode: {control_mode}")
