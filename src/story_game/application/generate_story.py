"""Turn one selected turn context into the next piece of story prose."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.llm import (
    GenerationConfigurationResolver,
    GenerationTask,
    LLMGenerationCall,
    StoryGenerationData,
    StoryGenerationPort,
    StoryGenerationRequest,
    StoryPromptSelectionResolver,
)
from story_game.application.story_prompt_sections import (
    configuration_text,
    story_state_text,
    world_state_text,
)
from story_game.application.story_turn_context_models import SelectedStoryTurnContext
from story_game.application.story_turn_errors import (
    StoryTurnError,
    StoryTurnErrorKind,
    story_model_failure,
)
from story_game.domain import GameConfiguration


@dataclass(frozen=True, slots=True)
class GenerateStoryRequest:
    """The already selected slice plus what the player just did.

    The configuration travels alongside the context because resolving the
    prompt needs the package reference, which the context does not carry.
    """

    context: SelectedStoryTurnContext
    configuration: GameConfiguration
    player_input: str

    def __post_init__(self) -> None:
        player_input = self.player_input.strip()
        if not player_input:
            raise ValueError("Die Spielereingabe darf nicht leer sein")
        object.__setattr__(self, "player_input", player_input)


class GenerateStory:
    """Prepare the story boundary and invoke the configured story model.

    Reads and writes no canonical state and never retries: an expected model
    failure stays a visible typed failure for the surrounding workflow.
    """

    def __init__(
        self,
        prompt_resolver: StoryPromptSelectionResolver,
        generation_configuration_resolver: GenerationConfigurationResolver,
        generator: StoryGenerationPort,
    ) -> None:
        self._prompt_resolver = prompt_resolver
        self._generation_configuration_resolver = generation_configuration_resolver
        self._generator = generator

    def apply(
        self, request: GenerateStoryRequest
    ) -> OperationResult[StoryGenerationData, StoryTurnError]:
        try:
            selection = self._prompt_resolver.resolve(request.configuration)
            generation = self._generation_configuration_resolver.resolve(
                GenerationTask.STORY
            )
            if isinstance(generation, Failure):
                return Failure(story_model_failure(generation.error))
            call = LLMGenerationCall(
                model_selection=generation.data.model_selection,
                generation_options=generation.data.generation_options,
                request=StoryGenerationRequest(
                    system_prompts=(
                        selection.task.text,
                        selection.boundary_directive.text,
                    ),
                    configuration=configuration_text(selection),
                    world_state=world_state_text(request.context),
                    story_state=story_state_text(request.context),
                    user_prompt=request.player_input,
                ),
            )
        except (KeyError, ValueError) as error:
            return Failure(
                StoryTurnError(
                    StoryTurnErrorKind.INVALID_CONFIGURATION,
                    str(error),
                )
            )

        generated = self._generator.generate(call)
        if isinstance(generated, Failure):
            return Failure(story_model_failure(generated.error))
        return Success(generated.data)
