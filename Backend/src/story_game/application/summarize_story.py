"""Condense one completed window of turns into a new summary segment."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.diagnostics import (
    DiagnosticsLog,
    NullDiagnosticsLog,
    SummaryGenerationFailed,
)
from story_game.application.llm import (
    GenerationConfigurationResolver,
    GenerationTask,
    LLMGenerationCall,
    StorySummaryPort,
    StorySummaryRequest,
    StorySummaryText,
    SummarizedTurn,
    SummaryPromptSelectionResolver,
)
from story_game.application.story_turn_errors import (
    StoryTurnError,
    StoryTurnErrorKind,
    story_model_failure,
)
from story_game.domain import GameConfiguration


@dataclass(frozen=True, slots=True)
class SummarizeStoryRequest:
    """The exact window of turns to condense into one new segment."""

    turns: tuple[SummarizedTurn, ...]
    configuration: GameConfiguration

    def __post_init__(self) -> None:
        if not self.turns:
            raise ValueError("Ein Zusammenfassungsfenster benötigt mindestens einen Zug")


class SummarizeStory:
    """Produce one new, self-contained summary segment for a turn window.

    Only the window's own turns are sent — never earlier segments or turns —
    so the call stays bounded by the configured summary interval regardless
    of how long the game has run. The result is appended to the chain of
    segments by the caller; this class never rewrites an existing segment.
    """

    def __init__(
        self,
        prompt_resolver: SummaryPromptSelectionResolver,
        generation_configuration_resolver: GenerationConfigurationResolver,
        summarizer: StorySummaryPort,
        diagnostics: DiagnosticsLog = NullDiagnosticsLog(),
    ) -> None:
        self._prompt_resolver = prompt_resolver
        self._generation_configuration_resolver = generation_configuration_resolver
        self._summarizer = summarizer
        self._diagnostics = diagnostics

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
            call = LLMGenerationCall(
                model_selection=generation.data.model_selection,
                generation_options=generation.data.generation_options,
                request=StorySummaryRequest(
                    system_prompts=(task.text,),
                    turns=request.turns,
                    language=request.configuration.language,
                ),
            )
        except (KeyError, ValueError) as error:
            return Failure(
                StoryTurnError(StoryTurnErrorKind.INVALID_CONFIGURATION, str(error))
            )

        self._diagnostics.trace(
            "summarize_story.call",
            turn_count=len(call.request.turns),
        )
        summarized = self._summarizer.summarize(call)
        if isinstance(summarized, Failure):
            self._diagnostics.record(SummaryGenerationFailed(error=summarized.error))
            return Failure(story_model_failure(summarized.error))
        self._diagnostics.trace("summarize_story.result", text=summarized.data.text)
        return Success(summarized.data)
