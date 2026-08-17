"""LM Studio structured-output adapter for one turn's change proposal."""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError as PydanticError

from story_game.application import Failure, Success
from story_game.application.llm import (
    CandidateCondition,
    CandidateEntity,
    CandidateEntityUpdate,
    CandidateFact,
    CandidateLink,
    LLMError,
    LLMErrorKind,
    LLMGenerationCall,
    TurnChangeCandidate,
    TurnExtractionPort,
    TurnExtractionRequest,
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


class _WireNewEntity(_WireModel):
    local_ref: str = Field(
        min_length=1,
        description="New short reference for an entity that did not exist before.",
    )
    kind: Literal["character", "location", "item", "creature", "faction"]
    label: str = Field(min_length=1)
    description: str = ""
    conditions: list[_WireCondition]
    aliases: list[str]


class _WireEntityUpdate(_WireModel):
    handle: str = Field(
        min_length=1,
        description="Handle of an entity listed in the world excerpt.",
    )
    description: str | None = None
    conditions: list[_WireCondition] | None = None
    aliases: list[str] | None = None


class _WireLink(_WireModel):
    source_ref: str = Field(
        min_length=1,
        description="One handle from the excerpt or one local_ref of a new entity.",
    )
    target_ref: str = Field(
        min_length=1,
        description="One handle from the excerpt or one local_ref of a new entity.",
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
            "One handle or local_ref; null when the fact has no single subject. "
            "Never combine references."
        ),
    )


class _WireCandidate(_WireModel):
    new_entities: list[_WireNewEntity]
    entity_updates: list[_WireEntityUpdate]
    added_links: list[_WireLink]
    removed_link_handles: list[str] = Field(
        description="Handles of relations the narration ended, e.g. a place left."
    )
    added_facts: list[_WireFact]
    removed_fact_handles: list[str] = Field(
        description="Handles of facts the narration made untrue."
    )
    scene_refs: list[str] = Field(
        description=(
            "Where the narration looks after this turn, most relevant first. "
            "Each entry is a handle or local_ref of a location. Repeat the "
            "current scene when it did not move; use an empty list only when no "
            "location applies at all."
        )
    )


class LmStudioTurnExtractionAdapter(TurnExtractionPort):
    """Request strict JSON and return only validated application candidates."""

    def __init__(self, client: LmStudioExtractionClient) -> None:
        self._client = client

    def extract(self, call: LLMGenerationCall[TurnExtractionRequest]):
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
                        name="turn_changes",
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
                    "LM Studio hat keinen gültigen Änderungsvorschlag geliefert.",
                )
            )


def _messages_for(request: TurnExtractionRequest) -> tuple[LmStudioChatMessage, ...]:
    sections = (
        "[language]\n" + request.language,
        "[world_state]\n" + request.world_state,
        "[narration]\n" + request.narration,
    )
    return (
        LmStudioChatMessage(role="system", content="\n\n".join(request.system_prompts)),
        LmStudioChatMessage(role="user", content="\n\n".join(sections)),
    )


def _candidate_from_wire(wire: _WireCandidate) -> TurnChangeCandidate:
    return TurnChangeCandidate(
        new_entities=tuple(
            CandidateEntity(
                item.local_ref,
                EntityKind(item.kind),
                item.label,
                item.description,
                _conditions(item.conditions),
                tuple(item.aliases),
            )
            for item in wire.new_entities
        ),
        entity_updates=tuple(
            CandidateEntityUpdate(
                item.handle,
                item.description,
                None if item.conditions is None else _conditions(item.conditions),
                None if item.aliases is None else tuple(item.aliases),
            )
            for item in wire.entity_updates
        ),
        added_links=tuple(
            CandidateLink(
                item.source_ref,
                item.target_ref,
                RelationKind(item.kind),
                item.quantity,
                item.description,
            )
            for item in wire.added_links
        ),
        removed_link_handles=tuple(wire.removed_link_handles),
        added_facts=tuple(
            CandidateFact(item.statement, item.subject_ref) for item in wire.added_facts
        ),
        removed_fact_handles=tuple(wire.removed_fact_handles),
        scene_refs=tuple(wire.scene_refs),
    )


def _conditions(items: list[_WireCondition]) -> tuple[CandidateCondition, ...]:
    return tuple(
        CandidateCondition(condition.name, condition.description) for condition in items
    )
