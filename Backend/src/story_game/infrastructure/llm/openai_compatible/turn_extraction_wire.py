"""Provider-agnostic structured-output mapping for one turn's change proposal."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from story_game.application.llm import (
    CandidateCondition,
    CandidateEntity,
    CandidateEntityUpdate,
    CandidateFact,
    CandidateLink,
    CandidateRemoval,
    CandidateSceneReference,
    LLMGenerationCall,
    TurnChangeCandidate,
    TurnExtractionRequest,
)
from story_game.domain import EntityKind, RelationKind

from ..json_schema import strict_json_schema
from .models import ChatMessage, ChatRequest, JsonSchema
from .wire_link import normalize_link_quantity


class _WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class _WireCondition(_WireModel):
    name: str = Field(min_length=1)
    description: str = ""


_EVIDENCE = Field(
    description=(
        "Verbatim quote from the narration that shows this change happened. "
        "Quote exactly; never paraphrase and never invent."
    ),
)


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


class _WireRemoval(_WireModel):
    handle: str = Field(min_length=1)


class _WireSceneReference(_WireModel):
    reference: str = Field(
        min_length=1,
        description="Handle or local_ref of a location.",
    )


class _WireNewEntityWithEvidence(_WireNewEntity):
    evidence: str = _EVIDENCE


class _WireEntityUpdateWithEvidence(_WireEntityUpdate):
    evidence: str = _EVIDENCE


class _WireLinkWithEvidence(_WireLink):
    evidence: str = _EVIDENCE


class _WireFactWithEvidence(_WireFact):
    evidence: str = _EVIDENCE


class _WireRemovalWithEvidence(_WireRemoval):
    evidence: str = _EVIDENCE


class _WireSceneReferenceWithEvidence(_WireSceneReference):
    evidence: str = _EVIDENCE


class _WireCandidate(_WireModel):
    new_entities: list[_WireNewEntity]
    entity_updates: list[_WireEntityUpdate]
    added_links: list[_WireLink]
    removed_links: list[_WireRemoval] = Field(
        description="Relations the narration ended, e.g. a place that was left."
    )
    added_facts: list[_WireFact]
    removed_facts: list[_WireRemoval] = Field(
        description="Facts the narration made untrue."
    )
    scene: list[_WireSceneReference] = Field(
        description=(
            "Where the narration looks after this turn, most relevant first. "
            "Repeat the current scene when it did not move; use an empty list "
            "only when no location applies at all."
        )
    )


class _WireCandidateWithEvidence(_WireCandidate):
    new_entities: list[_WireNewEntityWithEvidence]
    entity_updates: list[_WireEntityUpdateWithEvidence]
    added_links: list[_WireLinkWithEvidence]
    removed_links: list[_WireRemovalWithEvidence]
    added_facts: list[_WireFactWithEvidence]
    removed_facts: list[_WireRemovalWithEvidence]
    scene: list[_WireSceneReferenceWithEvidence]


def build_request(call: LLMGenerationCall[TurnExtractionRequest]) -> ChatRequest:
    wire_model = (
        _WireCandidateWithEvidence if call.request.with_evidence else _WireCandidate
    )
    return ChatRequest(
        model=call.model_selection.model_id,
        messages=_messages_for(call.request),
        temperature=call.generation_options.temperature,
        max_tokens=call.generation_options.max_output_tokens,
        response_format=JsonSchema(
            name="turn_changes",
            strict=True,
            schema=strict_json_schema(wire_model),
        ),
    )


def parse_response(call: LLMGenerationCall[TurnExtractionRequest], text: str) -> TurnChangeCandidate:
    wire_model = (
        _WireCandidateWithEvidence if call.request.with_evidence else _WireCandidate
    )
    wire = wire_model.model_validate_json(text)
    return _candidate_from_wire(wire)


def _messages_for(request: TurnExtractionRequest) -> tuple[ChatMessage, ...]:
    sections = (
        "[language]\n" + request.language,
        "[world_state]\n" + request.world_state,
        "[narration]\n" + request.narration,
    )
    return (
        ChatMessage(role="system", content="\n\n".join(request.system_prompts)),
        ChatMessage(role="user", content="\n\n".join(sections)),
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
                _evidence(item),
            )
            for item in wire.new_entities
        ),
        entity_updates=tuple(
            CandidateEntityUpdate(
                item.handle,
                item.description,
                None if item.conditions is None else _conditions(item.conditions),
                None if item.aliases is None else tuple(item.aliases),
                _evidence(item),
            )
            for item in wire.entity_updates
        ),
        added_links=tuple(
            CandidateLink(
                item.source_ref,
                item.target_ref,
                RelationKind(item.kind),
                normalize_link_quantity(
                    item.kind, item.quantity, item.source_ref, item.target_ref
                ),
                item.description,
                _evidence(item),
            )
            for item in wire.added_links
        ),
        removed_links=_removals(wire.removed_links),
        added_facts=tuple(
            CandidateFact(item.statement, item.subject_ref, _evidence(item))
            for item in wire.added_facts
        ),
        removed_facts=_removals(wire.removed_facts),
        scene=tuple(
            CandidateSceneReference(item.reference, _evidence(item))
            for item in wire.scene
        ),
    )


def _evidence(item: _WireModel) -> str | None:
    """Only the evidence-bearing schema variant carries a justification."""
    return getattr(item, "evidence", None)


def _removals(items: list[_WireRemoval]) -> tuple[CandidateRemoval, ...]:
    return tuple(CandidateRemoval(item.handle, _evidence(item)) for item in items)


def _conditions(items: list[_WireCondition]) -> tuple[CandidateCondition, ...]:
    return tuple(
        CandidateCondition(condition.name, condition.description) for condition in items
    )


__all__ = ["build_request", "parse_response"]
