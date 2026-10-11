"""Minimal initial world without Extraction (llm-integration §6c, provisional)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.initial_world_extraction import (
    WorldExtractionResult,
    default_run_title,
)
from story_game.application.initialization_errors import (
    StoryInitializationError,
    StoryInitializationErrorKind,
    StoryInitializationStage,
)
from story_game.application.initialization_models import ControllableCharacterSeed
from story_game.application.initialization_policy import validate_initialization_choices
from story_game.domain import (
    ActorProfile,
    ActorRole,
    DomainError,
    EntityKind,
    GameConfiguration,
    StableId,
    WorldEntity,
    WorldState,
)


@dataclass(frozen=True, slots=True)
class BuildSeedWorldStateRequest:
    configuration: GameConfiguration
    controllable_characters: tuple[ControllableCharacterSeed, ...]


class BuildSeedWorldState:
    """Build the initial world solely from the caller's character seeds.

    Used while world tracking is disabled. Every seed becomes one neutral
    character; confirmation assigns the player role as usual. No model output
    enters this world.
    """

    def __init__(
        self,
        new_id: Callable[[], StableId] = StableId.new,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._new_id = new_id
        self._now = now

    def apply(
        self, request: BuildSeedWorldStateRequest
    ) -> OperationResult[WorldExtractionResult, StoryInitializationError]:
        invalid = validate_initialization_choices(
            request.configuration,
            request.controllable_characters,
            StoryInitializationStage.WORLD_EXTRACTION,
        )
        if invalid is not None:
            return Failure(invalid)
        try:
            world = WorldState(
                entities=tuple(
                    WorldEntity(
                        id=self._new_id(),
                        kind=EntityKind.CHARACTER,
                        label=seed.name,
                        description=seed.description,
                        actor=ActorProfile(ActorRole.NEUTRAL),
                    )
                    for seed in request.controllable_characters
                )
            )
        except DomainError as error:
            return Failure(
                StoryInitializationError(
                    StoryInitializationErrorKind.DOMAIN_REJECTION,
                    StoryInitializationStage.WORLD_EXTRACTION,
                    str(error),
                )
            )
        return Success(WorldExtractionResult(world, default_run_title(self._now())))


__all__ = ["BuildSeedWorldState", "BuildSeedWorldStateRequest"]
