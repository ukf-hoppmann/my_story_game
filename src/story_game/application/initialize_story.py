"""Top-level orchestration for transient story and world initialization."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.initial_world_extraction import (
    ExtractInitialWorldState,
    ExtractInitialWorldStateRequest,
)
from story_game.application.initialization_errors import StoryInitializationError
from story_game.application.initialization_models import (
    InitializedStory,
    PlayerCharacterSeed,
)
from story_game.application.story_initialization import (
    GenerateInitialStoryState,
    GenerateInitialStoryStateRequest,
)
from story_game.domain import GameConfiguration


@dataclass(frozen=True, slots=True)
class InitializeStoryRequest:
    """All caller-owned input required before either model process starts."""

    configuration: GameConfiguration
    initial_prompt: str
    player_character: PlayerCharacterSeed | None = None

    def __post_init__(self) -> None:
        prompt = self.initial_prompt.strip()
        if not prompt:
            raise ValueError("Der Initialprompt darf nicht leer sein")
        object.__setattr__(self, "initial_prompt", prompt)


class InitializeStory:
    """Run opening generation and initial extraction as two ordered processes."""

    def __init__(
        self,
        story_generation: GenerateInitialStoryState,
        world_extraction: ExtractInitialWorldState,
    ) -> None:
        self._story_generation = story_generation
        self._world_extraction = world_extraction

    def apply(
        self, request: InitializeStoryRequest
    ) -> OperationResult[InitializedStory, StoryInitializationError]:
        generated = self._story_generation.apply(
            GenerateInitialStoryStateRequest(
                request.configuration,
                request.initial_prompt,
                request.player_character,
            )
        )
        if isinstance(generated, Failure):
            return generated
        extracted = self._world_extraction.apply(
            ExtractInitialWorldStateRequest(
                request.configuration,
                generated.data,
                request.player_character,
            )
        )
        if isinstance(extracted, Failure):
            return extracted
        return Success(InitializedStory(generated.data, extracted.data))
