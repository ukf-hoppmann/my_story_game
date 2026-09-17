"""Provider-agnostic request/response mapping for story generation.

Not provider-specific: how a ``StoryGenerationRequest`` becomes chat messages,
and how the response becomes ``StoryGenerationData``, is the same question
regardless of which OpenAI-compatible provider answers it.
"""

from __future__ import annotations

from story_game.application.llm import (
    LLMGenerationCall,
    StoryGenerationData,
    StoryGenerationRequest,
)

from ..json_schema import strict_json_schema
from .models import ChatMessage, ChatRequest, ChatResponse, JsonSchema
from .narration_wire import WireNarrationWithOptions

_SCHEMA = strict_json_schema(WireNarrationWithOptions)


def build_request(call: LLMGenerationCall[StoryGenerationRequest]) -> ChatRequest:
    return ChatRequest(
        model=call.model_selection.model_id,
        messages=_messages_for(call.request),
        temperature=call.generation_options.temperature,
        max_tokens=call.generation_options.max_output_tokens,
        response_format=JsonSchema(
            name="story_generation",
            strict=True,
            schema=_SCHEMA,
        ),
    )


def parse_response(response: ChatResponse) -> StoryGenerationData:
    wire = WireNarrationWithOptions.model_validate_json(response.text)
    return StoryGenerationData(wire.narration, tuple(wire.continuation_options))


def _messages_for(request: StoryGenerationRequest) -> tuple[ChatMessage, ...]:
    system_prompt = "\n\n".join(request.system_prompts)
    context = "\n\n".join(
        (
            "[configuration]\n" + request.configuration,
            "[world_state]\n" + request.world_state,
            "[story_state]\n" + request.story_state,
            "[user_prompt]\n" + request.user_prompt,
        )
    )
    return (
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=context),
    )


__all__ = ["build_request", "parse_response"]
