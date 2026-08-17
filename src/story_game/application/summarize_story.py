"""Roll the running story summary forward by one completed turn."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.llm import (
    GenerationConfigurationResolver,
    GenerationTask,
    LLMGenerationCall,
    StorySummaryPort,
    StorySummaryRequest,
    StorySummaryText,
    SummaryPromptSelectionResolver,
)
from story_game.application.story_turn_errors import (
    StoryTurnError,
    StoryTurnErrorKind,
    story_model_failure,
)
from story_game.domain import GameConfiguration, StoryState


@dataclass(frozen=True, slots=True)
class SummarizeStoryRequest:
    """The summary so far plus the turn that has just been narrated."""

    story: StoryState
    configuration: GameConfiguration
    player_input: str
    narration: str

    def __post_init__(self) -> None:
        for name, label in (
            ("player_input", "Die Spielereingabe"),
            ("narration", "Die Erzählung"),
        ):
            value = getattr(self, name).strip()
            if not value:
                raise ValueError(f"{label} darf nicht leer sein")
            object.__setattr__(self, name, value)


class SummarizeStory:
    """Produce the summary that replaces the current one.

    Only the previous summary and the new turn are sent: the summary already
    stands for everything before it, which keeps the call from growing with the
    game.
    """

    def __init__(
        self,
        prompt_resolver: SummaryPromptSelectionResolver,
        generation_configuration_resolver: GenerationConfigurationResolver,
        summarizer: StorySummaryPort,
    ) -> None:
        self._prompt_resolver = prompt_resolver
        self._generation_configuration_resolver = generation_configuration_resolver
        self._summarizer = summarizer

    def apply(
        self, request: SummarizeStoryRequest
    ) -> OperationResult[StorySummaryText, StoryTurnError]:
        try:
            task = self._prompt_resolver.resolve(
                request.configuration.prompt_package_id,
                request.configuration.prompt_package_version,
            )
            generation = self._generation_configuration_resolver.resolve(
                GenerationTask.SUMMARY
            )
            if isinstance(generation, Failure):
                return Failure(story_model_failure(generation.error))
            previous = request.story.summary
            call = LLMGenerationCall(
                model_selection=generation.data.model_selection,
                generation_options=generation.data.generation_options,
                request=StorySummaryRequest(
                    system_prompts=(task.text,),
                    player_input=request.player_input,
                    narration=request.narration,
                    language=request.configuration.language,
                    previous_summary=None if previous is None else previous.text,
                ),
            )
        except (KeyError, ValueError) as error:
            return Failure(
                StoryTurnError(StoryTurnErrorKind.INVALID_CONFIGURATION, str(error))
            )

        summarized = self._summarizer.summarize(call)
        if isinstance(summarized, Failure):
            return Failure(story_model_failure(summarized.error))
        return Success(summarized.data)
