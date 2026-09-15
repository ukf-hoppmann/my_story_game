"""Provider-agnostic request/response mapping for one summary-segment call."""

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
    turns = "\n\n".join(
        f"[turn {index}]\n"
        f"Spieler: {turn.player_input}\n"
        f"Erzählung: {turn.narration}"
        for index, turn in enumerate(request.turns, start=1)
    )
    sections = [
        "[language]\n" + request.language,
        "[turns]\n" + turns,
    ]
    return (
        ChatMessage(role="system", content="\n\n".join(request.system_prompts)),
        ChatMessage(role="user", content="\n\n".join(sections)),
    )


__all__ = ["build_request", "parse_response"]
