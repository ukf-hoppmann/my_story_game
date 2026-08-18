"""Application operation for generating one transient initialized story state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.diagnostics import (
    DiagnosticsLog,
    ModelCallFailed,
    NullDiagnosticsLog,
)
from story_game.application.initialization_errors import (
    StoryInitializationError,
    StoryInitializationErrorKind,
    StoryInitializationStage,
    model_failure,
)
from story_game.application.initialization_models import ControllableCharacterSeed
from story_game.application.initialization_policy import validate_initialization_choices
from story_game.application.llm import (
    GenerationConfigurationResolver,
    GenerationTask,
    LLMGenerationCall,
    StoryInitializationPort,
    StoryInitializationPromptResolver,
    StoryInitializationRequest,
)
from story_game.application.story_prompt_sections import configuration_text
from story_game.domain import GameConfiguration, StoryInitialization, StoryState


@dataclass(frozen=True, slots=True)
class GenerateInitialStoryStateRequest:
    """Input selected by the caller before any canonical game state exists."""

    configuration: GameConfiguration
    initial_prompt: str
    controllable_characters: tuple[ControllableCharacterSeed, ...] = ()

    def __post_init__(self) -> None:
        prompt = self.initial_prompt.strip()
        if not prompt:
            raise ValueError("Der Initialprompt darf nicht leer sein")
        object.__setattr__(self, "initial_prompt", prompt)


class GenerateInitialStoryState:
    """Create an opening StoryState without reading or writing canonical state."""

    def __init__(
        self,
        prompt_resolver: StoryInitializationPromptResolver,
        generation_configuration_resolver: GenerationConfigurationResolver,
        generator: StoryInitializationPort,
        now: Callable[[], datetime],
        diagnostics: DiagnosticsLog = NullDiagnosticsLog(),
    ) -> None:
        self._prompt_resolver = prompt_resolver
        self._generation_configuration_resolver = generation_configuration_resolver
        self._generator = generator
        self._now = now
        self._diagnostics = diagnostics

    def apply(
        self,
        request: GenerateInitialStoryStateRequest,
    ) -> OperationResult[StoryState, StoryInitializationError]:
        invalid = validate_initialization_choices(
            request.configuration,
            request.controllable_characters,
            StoryInitializationStage.STORY_GENERATION,
        )
        if invalid is not None:
            return Failure(invalid)
        try:
            selection = self._prompt_resolver.resolve(request.configuration)
            generation_configuration = self._generation_configuration_resolver.resolve(
                GenerationTask.STORY
            )
            if isinstance(generation_configuration, Failure):
                return Failure(
                    model_failure(
                        StoryInitializationStage.STORY_GENERATION,
                        generation_configuration.error,
                    )
                )
            call = LLMGenerationCall(
                model_selection=generation_configuration.data.model_selection,
                generation_options=generation_configuration.data.generation_options,
                request=StoryInitializationRequest(
                    system_prompts=(selection.task.text, selection.boundary_directive.text),
                    configuration=configuration_text(selection),
                    initial_prompt=request.initial_prompt,
                    controllable_characters=request.controllable_characters,
                ),
            )
        except (KeyError, ValueError) as error:
            return Failure(
                StoryInitializationError(
                    StoryInitializationErrorKind.INVALID_CONFIGURATION,
                    StoryInitializationStage.STORY_GENERATION,
                    str(error),
                )
            )

        self._diagnostics.trace(
            "generate_initial_story_state.call",
            system_prompts=call.request.system_prompts,
            configuration=call.request.configuration,
            initial_prompt=call.request.initial_prompt,
        )
        generated = self._generator.generate(call)
        if isinstance(generated, Failure):
            self._diagnostics.record(
                ModelCallFailed(task="story_initialization", error=generated.error)
            )
            return Failure(
                model_failure(
                    StoryInitializationStage.STORY_GENERATION,
                    generated.error,
                )
            )
        self._diagnostics.trace(
            "generate_initial_story_state.result", text=generated.data.text
        )

        initialization = StoryInitialization(
            prompt=request.initial_prompt,
            narration=generated.data.text,
            completed_at=self._now(),
        )
        return Success(StoryState(initialization=initialization))


