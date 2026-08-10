"""Application operation for generating one transient initialized story state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.llm import (
    GenerationConfigurationResolver,
    GenerationTask,
    LLMError,
    LLMErrorKind,
    LLMGenerationCall,
    StoryInitializationPort,
    StoryInitializationPromptResolver,
    StoryInitializationRequest,
    StoryPromptSelection,
)
from story_game.domain import GameConfiguration, StoryInitialization, StoryState


@dataclass(frozen=True, slots=True)
class GenerateInitialStoryStateRequest:
    """Input selected by the caller before any canonical game state exists."""

    configuration: GameConfiguration
    initial_prompt: str

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
    ) -> None:
        self._prompt_resolver = prompt_resolver
        self._generation_configuration_resolver = generation_configuration_resolver
        self._generator = generator
        self._now = now

    def apply(
        self,
        request: GenerateInitialStoryStateRequest,
    ) -> OperationResult[StoryState, LLMError]:
        try:
            selection = self._prompt_resolver.resolve(request.configuration)
            generation_configuration = self._generation_configuration_resolver.resolve(
                GenerationTask.STORY
            )
            if isinstance(generation_configuration, Failure):
                return generation_configuration
            call = LLMGenerationCall(
                model_selection=generation_configuration.data.model_selection,
                generation_options=generation_configuration.data.generation_options,
                request=StoryInitializationRequest(
                    system_prompts=(selection.task.text, selection.boundary_directive.text),
                    configuration=_configuration_text(selection),
                    initial_prompt=request.initial_prompt,
                ),
            )
        except (KeyError, ValueError) as error:
            return Failure(LLMError(LLMErrorKind.CONFIGURATION, str(error)))

        generated = self._generator.generate(call)
        if isinstance(generated, Failure):
            return generated

        initialization = StoryInitialization(
            prompt=request.initial_prompt,
            narration=generated.data.text,
            completed_at=self._now(),
        )
        return Success(StoryState(initialization=initialization))


def _configuration_text(selection: StoryPromptSelection) -> str:
    """Render resolved prompt meaning without exposing option IDs to the adapter."""
    resolved = selection
    return "\n".join(
        (
            f"Sprache: {resolved.language}",
            *(f"{item.category_id}: {item.description}" for item in resolved.options),
            "Erzählerische Grenzen: " + "; ".join(resolved.narrative_boundaries),
        )
    )
