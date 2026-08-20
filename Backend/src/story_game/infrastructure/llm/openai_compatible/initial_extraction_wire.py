"""Provider-agnostic structured-output mapping for initial WorldState extraction."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from story_game.application.llm import (
    CandidateCondition,
    CandidateEntity,
    CandidateFact,
    CandidateLink,
    InitialWorldExtractionRequest,
    LLMGenerationCall,
    WorldInitializationCandidate,
)
from story_game.domain import EntityKind, RelationKind

from ..json_schema import strict_json_schema
from .models import ChatMessage, ChatRequest, JsonSchema


class _WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class _WireCondition(_WireModel):
    name: str = Field(min_length=1)
    description: str = ""


class _WireEntity(_WireModel):
    local_ref: str = Field(
        min_length=1,
        description="Unique single reference for this entity.",
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
        description="Exactly one entity local_ref.",
    )
    target_ref: str = Field(
        min_length=1,
        description="Exactly one entity local_ref.",
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
            "Exactly one entity local_ref, or null when the fact has no single "
            "subject. Never combine references."
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
    suggested_title: str = Field(
        description=(
            "A short, evocative title for this opening scene, based only on the "
            "provided narration."
        ),
    )


def build_request(call: LLMGenerationCall[InitialWorldExtractionRequest]) -> ChatRequest:
    return ChatRequest(
        model=call.model_selection.model_id,
        messages=_messages_for(call.request),
        temperature=call.generation_options.temperature,
        max_tokens=call.generation_options.max_output_tokens,
        response_format=JsonSchema(
            name="world_initialization",
            strict=True,
            schema=strict_json_schema(_WireCandidate),
        ),
    )


def parse_response(text: str) -> WorldInitializationCandidate:
    wire = _WireCandidate.model_validate_json(text)
    return _candidate_from_wire(wire)


def _messages_for(
    request: InitialWorldExtractionRequest,
) -> tuple[ChatMessage, ...]:
    sections = [
        "[language]\n" + request.language,
        "[perspective]\n" + request.perspective,
        "[control_mode]\n" + request.control_mode,
        "[opening_narration]\n" + request.opening_narration,
    ]
    return (
        ChatMessage(role="system", content="\n\n".join(request.system_prompts)),
        ChatMessage(role="user", content="\n\n".join(sections)),
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
        suggested_title=wire.suggested_title,
    )


__all__ = ["build_request", "parse_response"]
