"""Build a canonical initial WorldState from one structured model candidate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.initialization_errors import (
    StoryInitializationError,
    StoryInitializationErrorKind,
    StoryInitializationStage,
    extraction_model_failure,
)
from story_game.application.initialization_models import PlayerCharacterSeed
from story_game.application.initialization_policy import validate_initialization_choices
from story_game.application.llm import (
    GenerationConfigurationResolver,
    GenerationTask,
    CandidateEntity,
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
    StableId,
    StoryState,
    WorldEntity,
    WorldState,
)


_PLAYER_REFERENCE = "player_character"


@dataclass(frozen=True, slots=True)
class ExtractInitialWorldStateRequest:
    """Input for extraction after opening prose has been generated."""

    configuration: GameConfiguration
    story_state: StoryState
    player_character: PlayerCharacterSeed | None = None


class ExtractInitialWorldState:
    """Extract and validate an all-or-nothing initial canonical world."""

    def __init__(
        self,
        prompt_resolver: InitialExtractionPromptSelectionResolver,
        generation_configuration_resolver: GenerationConfigurationResolver,
        extractor: InitialWorldExtractionPort,
        new_id: Callable[[], StableId] = StableId.new,
    ) -> None:
        self._prompt_resolver = prompt_resolver
        self._generation_configuration_resolver = generation_configuration_resolver
        self._extractor = extractor
        self._new_id = new_id

    def apply(
        self, request: ExtractInitialWorldStateRequest
    ) -> OperationResult[WorldState, StoryInitializationError]:
        invalid = validate_initialization_choices(
            request.configuration,
            request.player_character,
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
            extracted = self._extractor.extract(
                LLMGenerationCall(
                    model_selection=generation.data.model_selection,
                    generation_options=generation.data.generation_options,
                    request=InitialWorldExtractionRequest(
                        system_prompts=_system_prompts(
                            selection.task.text, request.player_character
                        ),
                        opening_narration=initialization.narration,
                        language=request.configuration.language,
                        perspective=request.configuration.prompt_profile.perspective,
                        control_mode=request.configuration.prompt_profile.control_mode,
                        player_character=request.player_character,
                    ),
                )
            )
        except (KeyError, ValueError) as error:
            return Failure(
                StoryInitializationError(
                    StoryInitializationErrorKind.INVALID_CONFIGURATION,
                    StoryInitializationStage.WORLD_EXTRACTION,
                    str(error),
                )
            )
        if isinstance(extracted, Failure):
            return Failure(extraction_model_failure(extracted.error))
        return _build_world(extracted.data, request.player_character, self._new_id)


def _build_world(
    candidate: WorldInitializationCandidate,
    player_character: PlayerCharacterSeed | None,
    new_id: Callable[[], StableId],
) -> OperationResult[WorldState, StoryInitializationError]:
    reference_ids: dict[str, StableId] = {}
    entities: list[WorldEntity] = []
    try:
        if player_character is not None:
            player_id = new_id()
            reference_ids[_PLAYER_REFERENCE] = player_id
            entities.append(
                WorldEntity(
                    id=player_id,
                    kind=EntityKind.CHARACTER,
                    label=player_character.name,
                    description=player_character.description,
                    actor=ActorProfile(ActorRole.PLAYER),
                )
            )

        for item in candidate.entities:
            reference = _reference_key(item.local_ref)
            if reference == _PLAYER_REFERENCE or reference in reference_ids:
                return _reference_failure(
                    f"Die lokale Referenz {item.local_ref!r} ist reserviert oder doppelt."
                )
            if player_character is not None and _duplicates_player(item, player_character):
                return _reference_failure(
                    "Eine extrahierte Entität dupliziert Name oder Alias des Spielercharakters."
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
            for item in candidate.links
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


def _reference_key(value: str) -> str:
    return value.strip().casefold()


def _system_prompts(
    task_prompt: str,
    player_character: PlayerCharacterSeed | None,
) -> tuple[str, ...]:
    if player_character is None:
        return (task_prompt,)
    name = player_character.name
    return (
        task_prompt,
        (
            f"VERBINDLICHE SPIELERREFERENZ: Der bekannte Spieler heißt {name!r}. "
            f"entities darf {name!r} weder als local_ref, label noch alias enthalten. "
            f"Jede source_ref, target_ref oder subject_ref für {name!r} muss exakt "
            "player_character sein. Prüfe diese Ersetzung unmittelbar vor der Antwort."
        ),
    )


def _resolve_reference(value: str, references: dict[str, StableId]) -> StableId:
    return references[_reference_key(value)]


def _duplicates_player(item: CandidateEntity, player: PlayerCharacterSeed) -> bool:
    player_name = player.name.casefold()
    return item.label.casefold() == player_name or any(
        alias.casefold() == player_name for alias in item.aliases
    )


def _reference_failure(message: str) -> Failure[StoryInitializationError]:
    return Failure(
        StoryInitializationError(
            StoryInitializationErrorKind.INVALID_CANDIDATE_REFERENCE,
            StoryInitializationStage.WORLD_EXTRACTION,
            message,
        )
    )
