"""LM Studio structured-output adapter for initial WorldState extraction."""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError as PydanticError

from story_game.application import Failure, Success
from story_game.application.llm import (
    CandidateCondition,
    CandidateEntity,
    CandidateFact,
    CandidateLink,
    InitialWorldExtractionPort,
    InitialWorldExtractionRequest,
    LLMError,
    LLMErrorKind,
    LLMGenerationCall,
    WorldInitializationCandidate,
    reserved_reference,
)
from story_game.domain import EntityKind, RelationKind

from .adapter import _map_error
from .errors import LmStudioClientError
from .models import (
    LmStudioChatMessage,
    LmStudioChatRequest,
    LmStudioChatResponse,
    LmStudioJsonSchema,
)


class LmStudioExtractionClient(Protocol):
    def complete(self, request: LmStudioChatRequest) -> LmStudioChatResponse: ...


class _WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class _WireCondition(_WireModel):
    name: str = Field(min_length=1)
    description: str = ""


class _WireEntity(_WireModel):
    local_ref: str = Field(
        min_length=1,
        description="Unique single reference; never one of the known controllable characters.",
    )
    kind: Literal["character", "location", "item", "creature", "faction"]
    label: str = Field(
        min_length=1,
        description="Identity label; for a character use the character's proper name.",
    )
    description: str = ""
    conditions: list[_WireCondition]
    aliases: list[str]


class _WireLink(_WireModel):
    source_ref: str = Field(
        min_length=1,
        description=(
            "Exactly one entity local_ref, or one of the reserved controllable-"
            "character references (see [known_controllable_characters])."
        ),
    )
    target_ref: str = Field(
        min_length=1,
        description=(
            "Exactly one entity local_ref, or one of the reserved controllable-"
            "character references (see [known_controllable_characters])."
        ),
    )
    kind: Literal[
        "located_in",
        "possesses",
        "contains",
        "member_of",
        "knows",
        "allied_with",
        "hostile_to",
        "related_to",
    ]
    quantity: int | None = Field(default=None, ge=1)
    description: str = ""


class _WireFact(_WireModel):
    statement: str = Field(min_length=1)
    subject_ref: str | None = Field(
        default=None,
        description=(
            "Exactly one entity local_ref, or one of the reserved controllable-"
            "character references (see [known_controllable_characters]); use null "
            "when the fact has no single subject. Never combine references."
        ),
    )


class _WireCandidate(_WireModel):
    entities: list[_WireEntity]
    links: list[_WireLink]
    facts: list[_WireFact]
    scene_refs: list[str] = Field(
        description=(
            "Local refs of the locations the opening is set in, most relevant first. "
            "Each entry must be an entity local_ref of kind location. This is where "
            "the narration looks, not where an entity is. Use an empty list only when "
            "the opening establishes no location at all."
        ),
    )


class LmStudioInitialWorldExtractionAdapter(InitialWorldExtractionPort):
    """Request strict JSON and return only validated application candidates."""

    def __init__(self, client: LmStudioExtractionClient) -> None:
        self._client = client

    def extract(
        self,
        call: LLMGenerationCall[InitialWorldExtractionRequest],
    ):
        if call.model_selection.provider_id != "lmstudio":
            return Failure(
                LLMError(
                    LLMErrorKind.CONFIGURATION,
                    "Der LM-Studio-Adapter wurde mit einem anderen Provider aufgerufen.",
                )
            )
        try:
            response = self._client.complete(
                LmStudioChatRequest(
                    model=call.model_selection.model_id,
                    messages=_messages_for(call.request),
                    temperature=call.generation_options.temperature,
                    max_tokens=call.generation_options.max_output_tokens,
                    response_format=LmStudioJsonSchema(
                        name="world_initialization",
                        strict=True,
                        schema=_WireCandidate.model_json_schema(),
                    ),
                )
            )
        except LmStudioClientError as error:
            return Failure(_map_error(error))

        try:
            wire = _WireCandidate.model_validate_json(response.text)
            return Success(_candidate_from_wire(wire))
        except (PydanticError, ValueError):
            return Failure(
                LLMError(
                    LLMErrorKind.INVALID_RESPONSE,
                    "LM Studio hat keinen gültigen Initial-WorldState-Candidate geliefert.",
                )
            )


def _messages_for(
    request: InitialWorldExtractionRequest,
) -> tuple[LmStudioChatMessage, ...]:
    sections = [
        "[language]\n" + request.language,
        "[perspective]\n" + request.perspective,
        "[control_mode]\n" + request.control_mode,
    ]
    system_sections = [*request.system_prompts]
    if request.controllable_characters:
        lines = [
            f"- Referenz {reserved_reference(index)}: Name={character.name}, "
            f"Beschreibung={character.description or 'Keine zusätzliche Beschreibung.'}"
            for index, character in enumerate(request.controllable_characters)
        ]
        system_sections.append("[known_controllable_characters]\n" + "\n".join(lines))
    sections.append("[opening_narration]\n" + request.opening_narration)
    return (
        LmStudioChatMessage(role="system", content="\n\n".join(system_sections)),
        LmStudioChatMessage(role="user", content="\n\n".join(sections)),
    )


def _candidate_from_wire(wire: _WireCandidate) -> WorldInitializationCandidate:
    return WorldInitializationCandidate(
        entities=tuple(
            CandidateEntity(
                item.local_ref,
                EntityKind(item.kind),
                item.label,
                item.description,
                tuple(
                    CandidateCondition(condition.name, condition.description)
                    for condition in item.conditions
                ),
                tuple(item.aliases),
            )
            for item in wire.entities
        ),
        links=tuple(
            CandidateLink(
                item.source_ref,
                item.target_ref,
                RelationKind(item.kind),
                item.quantity,
                item.description,
            )
            for item in wire.links
        ),
        facts=tuple(
            CandidateFact(item.statement, item.subject_ref) for item in wire.facts
        ),
        scene_refs=tuple(wire.scene_refs),
    )
