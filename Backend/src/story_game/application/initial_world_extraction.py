"""Build a canonical initial WorldState from one structured model candidate."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.diagnostics import (
    DiagnosticsLog,
    ModelCallFailed,
    NullDiagnosticsLog,
    ProposalRejected,
)
from story_game.application.initialization_errors import (
    StoryInitializationError,
    StoryInitializationErrorKind,
    StoryInitializationStage,
    extraction_model_failure,
)
from story_game.application.initialization_models import ControllableCharacterSeed
from story_game.application.initialization_policy import validate_initialization_choices
from story_game.application.llm import (
    GenerationConfigurationResolver,
    GenerationTask,
    CandidateLink,
    InitialExtractionPromptSelectionResolver,
    InitialWorldExtractionPort,
    InitialWorldExtractionRequest,
    LLMGenerationCall,
    WorldInitializationCandidate,
)
from story_game.domain import (
    ActorProfile,
    ActorRole,
    Condition,
    DomainError,
    EntityKind,
    EntityLink,
    Fact,
    GameConfiguration,
    RelationKind,
    StableId,
    StoryState,
    WorldEntity,
    WorldState,
)


@dataclass(frozen=True, slots=True)
class ExtractInitialWorldStateRequest:
    """Input for extraction after opening prose has been generated."""

    configuration: GameConfiguration
    story_state: StoryState
    controllable_characters: tuple[ControllableCharacterSeed, ...] = ()


@dataclass(frozen=True, slots=True)
class WorldExtractionResult:
    """The canonical proposal world plus a non-canonical title suggestion."""

    world_state: WorldState
    suggested_title: str


class ExtractInitialWorldState:
    """Extract and validate an all-or-nothing initial canonical world."""

    def __init__(
        self,
        prompt_resolver: InitialExtractionPromptSelectionResolver,
        generation_configuration_resolver: GenerationConfigurationResolver,
        extractor: InitialWorldExtractionPort,
        new_id: Callable[[], StableId] = StableId.new,
        diagnostics: DiagnosticsLog = NullDiagnosticsLog(),
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._prompt_resolver = prompt_resolver
        self._generation_configuration_resolver = generation_configuration_resolver
        self._extractor = extractor
        self._new_id = new_id
        self._diagnostics = diagnostics
        self._now = now

    def apply(
        self, request: ExtractInitialWorldStateRequest
    ) -> OperationResult[WorldExtractionResult, StoryInitializationError]:
        invalid = validate_initialization_choices(
            request.configuration,
            request.controllable_characters,
            StoryInitializationStage.WORLD_EXTRACTION,
        )
        if invalid is not None:
            return Failure(invalid)
        initialization = request.story_state.initialization
        if initialization is None:
            return Failure(
                StoryInitializationError(
                    StoryInitializationErrorKind.INVALID_CONFIGURATION,
                    StoryInitializationStage.WORLD_EXTRACTION,
                    "Die WorldState-Initialisierung benötigt eine fertige Eröffnungsprosa.",
                )
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
                return Failure(extraction_model_failure(generation.error))
            call = LLMGenerationCall(
                model_selection=generation.data.model_selection,
                generation_options=generation.data.generation_options,
                request=InitialWorldExtractionRequest(
                    system_prompts=(
                        selection.task.text,
                        *(directive.text for directive in selection.directives),
                    ),
                    opening_narration=initialization.narration,
                    language=request.configuration.language,
                    perspective=request.configuration.prompt_profile.perspective,
                    control_mode=request.configuration.prompt_profile.control_mode,
                ),
            )
            self._diagnostics.trace(
                "extract_initial_world_state.call",
                system_prompts=call.request.system_prompts,
                opening_narration=call.request.opening_narration,
            )
            extracted = self._extractor.extract(call)
        except (KeyError, ValueError) as error:
            return Failure(
                StoryInitializationError(
                    StoryInitializationErrorKind.INVALID_CONFIGURATION,
                    StoryInitializationStage.WORLD_EXTRACTION,
                    str(error),
                )
            )
        if isinstance(extracted, Failure):
            self._diagnostics.record(
                ModelCallFailed(task="initial_world_extraction", error=extracted.error)
            )
            return Failure(extraction_model_failure(extracted.error))
        self._diagnostics.trace(
            "extract_initial_world_state.candidate", candidate=extracted.data
        )
        built = _build_world(extracted.data, self._new_id)
        if isinstance(built, Failure):
            self._diagnostics.record(ProposalRejected(reason=str(built.error)))
            return built
        return Success(
            WorldExtractionResult(
                world_state=built.data,
                suggested_title=(
                    extracted.data.suggested_title.strip()
                    or default_run_title(self._now())
                ),
            )
        )


def _build_world(
    candidate: WorldInitializationCandidate,
    new_id: Callable[[], StableId],
) -> OperationResult[WorldState, StoryInitializationError]:
    """Build a proposal WorldState where every character is still neutral.

    No entity is created as, or reserved for, "the" player character here:
    every extracted character (including one that will later be confirmed as
    player-controlled) is built the same way, with the neutral actor role.
    Assigning player roles, dropping caller-rejected entities, and enforcing
    "exactly one player in Player Mode" are Application decisions made later,
    when the caller confirms the proposal — see
    ``confirm_game_run_proposal.py``.
    """
    reference_ids: dict[str, StableId] = {}
    entities: list[WorldEntity] = []
    try:
        for item in candidate.entities:
            reference = _reference_key(item.local_ref)
            if reference in reference_ids:
                return _reference_failure(
                    f"Die lokale Referenz {item.local_ref!r} ist doppelt."
                )
            entity_id = new_id()
            reference_ids[reference] = entity_id
            entities.append(
                WorldEntity(
                    id=entity_id,
                    kind=item.kind,
                    label=item.label,
                    description=item.description,
                    actor=(
                        ActorProfile(ActorRole.NEUTRAL)
                        if item.kind is EntityKind.CHARACTER
                        else None
                    ),
                    conditions=tuple(
                        Condition(condition.name, condition.description)
                        for condition in item.conditions
                    ),
                    aliases=item.aliases,
                )
            )

        links = tuple(
            EntityLink(
                id=new_id(),
                source_id=_resolve_reference(item.source_ref, reference_ids),
                target_id=_resolve_reference(item.target_ref, reference_ids),
                kind=item.kind,
                quantity=item.quantity,
                description=item.description,
            )
            for item in _deduplicated_links(candidate.links)
        )
        facts = tuple(
            Fact(
                id=new_id(),
                statement=item.statement,
                subject_id=(
                    None
                    if item.subject_ref is None
                    else _resolve_reference(item.subject_ref, reference_ids)
                ),
            )
            for item in candidate.facts
        )
        scene_location_ids = tuple(
            _resolve_reference(reference, reference_ids)
            for reference in candidate.scene_refs
        )
        return Success(
            WorldState(
                entities=tuple(entities),
                links=links,
                facts=facts,
                scene_location_ids=scene_location_ids,
            )
        )
    except KeyError as error:
        return _reference_failure(f"Unbekannte lokale Referenz: {error.args[0]!r}.")
    except DomainError as error:
        return Failure(
            StoryInitializationError(
                StoryInitializationErrorKind.DOMAIN_REJECTION,
                StoryInitializationStage.WORLD_EXTRACTION,
                str(error),
            )
        )


def default_run_title(now: datetime) -> str:
    return f"Neue Geschichte – {now:%d.%m.%Y %H:%M}"


def _reference_key(value: str) -> str:
    return value.strip().casefold()


def _deduplicated_links(links: tuple[CandidateLink, ...]) -> tuple[CandidateLink, ...]:
    """Collapse exact-duplicate wire links, keeping first occurrence.

    A model occasionally repeats the exact same relation twice (identical
    source, target, kind, quantity and description). That carries no
    additional information and is silently redundant, unlike two genuinely
    different targets for the same source-and-kind, which is a real conflict
    and must still surface as a Domain rejection.
    """
    seen: set[tuple[str, str, RelationKind, int | None, str]] = set()
    deduplicated: list[CandidateLink] = []
    for item in links:
        key = (
            _reference_key(item.source_ref),
            _reference_key(item.target_ref),
            item.kind,
            item.quantity,
            item.description,
        )
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(item)
    return tuple(deduplicated)


def _resolve_reference(value: str, references: dict[str, StableId]) -> StableId:
    return references[_reference_key(value)]


def _reference_failure(message: str) -> Failure[StoryInitializationError]:
    return Failure(
        StoryInitializationError(
            StoryInitializationErrorKind.INVALID_CANDIDATE_REFERENCE,
            StoryInitializationStage.WORLD_EXTRACTION,
            message,
        )
    )
