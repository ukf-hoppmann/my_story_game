"""Ask the model which changes one turn's prose implies for the world."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.diagnostics import (
    DiagnosticsLog,
    ModelCallFailed,
    NullDiagnosticsLog,
)
from story_game.application.llm import (
    ExtractionPromptSelectionResolver,
    GenerationConfigurationResolver,
    GenerationTask,
    LLMGenerationCall,
    TurnChangeCandidate,
    TurnExtractionPort,
    TurnExtractionRequest,
)
from story_game.application.story_prompt_sections import (
    TurnExtractionProjection,
    extraction_projection,
)
from story_game.application.story_turn_context_models import SelectedStoryTurnContext
from story_game.application.story_turn_errors import (
    StoryTurnError,
    StoryTurnErrorKind,
    story_model_failure,
)
from story_game.domain import GameConfiguration


@dataclass(frozen=True, slots=True)
class ExtractStoryTurnChangesRequest:
    context: SelectedStoryTurnContext
    configuration: GameConfiguration
    narration: str
    with_evidence: bool = True

    def __post_init__(self) -> None:
        narration = self.narration.strip()
        if not narration:
            raise ValueError("Die Erzählung darf nicht leer sein")
        object.__setattr__(self, "narration", narration)


@dataclass(frozen=True, slots=True)
class ExtractedTurnChanges:
    """The untrusted proposal together with the handles it was phrased in.

    The projection travels with the candidate because only it can turn the
    handles back into stable IDs, and it must be the very same one the model
    saw.
    """

    candidate: TurnChangeCandidate
    projection: TurnExtractionProjection


class ExtractStoryTurnChanges:
    """Compare new prose against the current world and collect a proposal.

    The player's input stays out of this call on purpose: what actually
    happened is what the narration says, not what the player attempted.
    """

    def __init__(
        self,
        prompt_resolver: ExtractionPromptSelectionResolver,
        generation_configuration_resolver: GenerationConfigurationResolver,
        extractor: TurnExtractionPort,
        diagnostics: DiagnosticsLog = NullDiagnosticsLog(),
    ) -> None:
        self._prompt_resolver = prompt_resolver
        self._generation_configuration_resolver = generation_configuration_resolver
        self._extractor = extractor
        self._diagnostics = diagnostics

    def apply(
        self, request: ExtractStoryTurnChangesRequest
    ) -> OperationResult[ExtractedTurnChanges, StoryTurnError]:
        projection = extraction_projection(request.context)
        self._diagnostics.trace(
            "extract_story_turn_changes.request",
            narration=request.narration,
            world_state=projection.text,
        )
        try:
            selection = self._prompt_resolver.resolve(
                request.configuration.prompt_package_id,
                request.configuration.prompt_package_version,
            )
            generation = self._generation_configuration_resolver.resolve(
                GenerationTask.EXTRACTION
            )
            if isinstance(generation, Failure):
                return Failure(story_model_failure(generation.error))
            call = LLMGenerationCall(
                model_selection=generation.data.model_selection,
                generation_options=generation.data.generation_options,
                request=TurnExtractionRequest(
                    system_prompts=(
                        selection.task.text,
                        selection.option.description,
                        *(directive.text for directive in selection.directives),
                    ),
                    narration=request.narration,
                    world_state=projection.text,
                    language=request.configuration.language,
                    with_evidence=request.with_evidence,
                ),
            )
        except (KeyError, ValueError) as error:
            return Failure(
                StoryTurnError(StoryTurnErrorKind.INVALID_CONFIGURATION, str(error))
            )

        extracted = self._extractor.extract(call)
        if isinstance(extracted, Failure):
            self._diagnostics.record(
                ModelCallFailed(task="extraction", error=extracted.error)
            )
            return Failure(story_model_failure(extracted.error))
        self._diagnostics.trace("extract_story_turn_changes.result", candidate=extracted.data)
        return Success(ExtractedTurnChanges(extracted.data, projection))
