"""Generate a caller-reviewable run proposal without persisting anything."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeAlias

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.diagnostics import DiagnosticsLog, NullDiagnosticsLog
from story_game.application.game_models import CachedGameRunProposal, GameRunProposal
from story_game.application.initialization_errors import StoryInitializationError
from story_game.application.initialization_models import ControllableCharacterSeed
from story_game.application.initialize_story import InitializeStory, InitializeStoryRequest
from story_game.application.ports import InitialProposalStore
from story_game.application.run_initiator import RunInitiator
from story_game.domain import EntityKind, GameConfiguration, StableId


ProposeGameRunError: TypeAlias = StoryInitializationError


def _required(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{label} darf nicht leer sein")
    return value


@dataclass(frozen=True, slots=True)
class ProposeGameRunRequest:
    """Caller input needed to generate one transient, unconfirmed proposal."""

    configuration: GameConfiguration
    initial_prompt: str
    initiator: RunInitiator
    controllable_characters: tuple[ControllableCharacterSeed, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "initial_prompt",
            _required(self.initial_prompt, "Der Initialprompt"),
        )


class ProposeGameRun:
    """Run story generation and initial extraction, then cache the result.

    Nothing here is canonical: no ``GameRun`` is created, and the returned
    ``WorldState`` holds every extracted character as a neutral entity — the
    model never designates a player character (see
    ``initial_world_extraction.py``). The caller confirms or discards this
    proposal separately via ``ConfirmGameRunProposal``.
    """

    def __init__(
        self,
        story_initializer: InitializeStory,
        proposal_store: InitialProposalStore,
        *,
        new_id: Callable[[], StableId] = StableId.new,
        diagnostics: DiagnosticsLog = NullDiagnosticsLog(),
    ) -> None:
        self._story_initializer = story_initializer
        self._proposal_store = proposal_store
        self._new_id = new_id
        self._diagnostics = diagnostics

    def apply(
        self, request: ProposeGameRunRequest
    ) -> OperationResult[GameRunProposal, ProposeGameRunError]:
        self._diagnostics.trace("propose_game_run.start")
        initialized = self._story_initializer.apply(
            InitializeStoryRequest(
                request.configuration,
                request.initial_prompt,
                request.controllable_characters,
            )
        )
        if isinstance(initialized, Failure):
            return initialized

        proposal_id = self._new_id()
        self._proposal_store.save(
            proposal_id,
            CachedGameRunProposal(
                issuer=request.initiator.issuer,
                subject=request.initiator.subject,
                configuration=request.configuration,
                story_state=initialized.data.story_state,
                world_state=initialized.data.world_state,
            ),
        )
        self._diagnostics.trace("propose_game_run.done", proposal_id=str(proposal_id))
        return Success(
            GameRunProposal(
                proposal_id=proposal_id,
                story_state=initialized.data.story_state,
                world_state=initialized.data.world_state,
                suggested_player_entity_ids=_suggested_player_entity_ids(
                    initialized.data.world_state.entities,
                    request.controllable_characters,
                ),
            )
        )


def _suggested_player_entity_ids(
    entities: tuple, controllable_characters: tuple[ControllableCharacterSeed, ...]
) -> tuple[StableId, ...]:
    """Default the UI's player/NPC switch by name match against the seeds.

    A pure display suggestion, not a decision: nothing here assigns a player
    role. The caller confirms the actual role per character in
    ``ConfirmGameRunProposal``.
    """
    seed_names = {seed.name.casefold() for seed in controllable_characters}
    if not seed_names:
        return ()
    return tuple(
        entity.id
        for entity in entities
        if entity.kind is EntityKind.CHARACTER and entity.label.casefold() in seed_names
    )
