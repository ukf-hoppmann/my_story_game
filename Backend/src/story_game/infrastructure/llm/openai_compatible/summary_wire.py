"""Provider-agnostic request/response mapping for the rolling summary call."""

from __future__ import annotations

from story_game.application.llm import (
    LLMGenerationCall,
    StorySummaryRequest,
    StorySummaryText,
)

from .models import ChatMessage, ChatRequest, ChatResponse


def build_request(call: LLMGenerationCall[StorySummaryRequest]) -> ChatRequest:
    return ChatRequest(
        model=call.model_selection.model_id,
        messages=_messages_for(call.request),
        temperature=call.generation_options.temperature,
        max_tokens=call.generation_options.max_output_tokens,
    )


def parse_response(response: ChatResponse) -> StorySummaryText:
    return StorySummaryText(response.text)


def _messages_for(request: StorySummaryRequest) -> tuple[ChatMessage, ...]:
    sections = [
        "[language]\n" + request.language,
        "[previous_summary]\n"
        + (request.previous_summary or "Es gibt noch keine Zusammenfassung."),
        "[player_input]\n" + request.player_input,
        "[narration]\n" + request.narration,
    ]
    return (
        ChatMessage(role="system", content="\n\n".join(request.system_prompts)),
        ChatMessage(role="user", content="\n\n".join(sections)),
    )


__all__ = ["build_request", "parse_response"]
