"""Provider-agnostic request/response mapping for the opening-prose call."""

from __future__ import annotations

from story_game.application.llm import (
    InitialStoryText,
    LLMGenerationCall,
    StoryInitializationRequest,
)

from ..json_schema import strict_json_schema
from .models import ChatMessage, ChatRequest, ChatResponse, JsonSchema
from .narration_wire import WireNarrationWithOptions

_SCHEMA = strict_json_schema(WireNarrationWithOptions)


def build_request(call: LLMGenerationCall[StoryInitializationRequest]) -> ChatRequest:
    return ChatRequest(
        model=call.model_selection.model_id,
        messages=_messages_for(call.request),
        temperature=call.generation_options.temperature,
        max_tokens=call.generation_options.max_output_tokens,
        response_format=JsonSchema(
            name="story_initialization",
            strict=True,
            schema=_SCHEMA,
        ),
    )


def parse_response(response: ChatResponse) -> InitialStoryText:
    wire = WireNarrationWithOptions.model_validate_json(response.text)
    return InitialStoryText(wire.narration, tuple(wire.continuation_options))


def _messages_for(request: StoryInitializationRequest) -> tuple[ChatMessage, ...]:
    sections = [
        "[configuration]\n" + request.configuration,
        "[initial_prompt]\n" + request.initial_prompt,
    ]
    if request.controllable_characters:
        lines = [
            f"- Name: {character.name}\n"
            f"  Beschreibung: {character.description or 'Keine zusätzliche Beschreibung.'}"
            for character in request.controllable_characters
        ]
        sections.append("[controllable_characters]\n" + "\n".join(lines))
    return (
        ChatMessage(role="system", content="\n\n".join(request.system_prompts)),
        ChatMessage(role="user", content="\n\n".join(sections)),
    )


__all__ = ["build_request", "parse_response"]
