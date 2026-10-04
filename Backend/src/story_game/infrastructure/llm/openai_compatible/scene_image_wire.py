"""Provider-agnostic request/response mapping for scene-image prompt calls."""

from __future__ import annotations

from story_game.application.llm import (
    CompactImagePromptRequest,
    LLMGenerationCall,
    SceneImagePromptRequest,
    SceneImagePromptText,
)

from .models import ChatMessage, ChatRequest, ChatResponse


def build_prompt_request(call: LLMGenerationCall[SceneImagePromptRequest]) -> ChatRequest:
    request = call.request
    turns = "\n\n".join(
        f"[turn {index}]\nSpieler: {turn.player_input}\nErzählung: {turn.narration}"
        for index, turn in enumerate(request.turns, start=1)
    )
    return _chat(call, request.system_prompts, f"[language]\n{request.language}\n\n[turns]\n{turns}")


def build_compact_request(call: LLMGenerationCall[CompactImagePromptRequest]) -> ChatRequest:
    request = call.request
    return _chat(
        call,
        request.system_prompts,
        f"[max_words]\n{request.max_words}\n\n[prompt]\n{request.prompt}",
    )


def parse_response(response: ChatResponse) -> SceneImagePromptText:
    text = response.text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1]
    return SceneImagePromptText(text)


def _chat(call, system_prompts: tuple[str, ...], user: str) -> ChatRequest:
    return ChatRequest(
        model=call.model_selection.model_id,
        messages=(
            ChatMessage(role="system", content="\n\n".join(system_prompts)),
            ChatMessage(role="user", content=user),
        ),
        temperature=call.generation_options.temperature,
        max_tokens=call.generation_options.max_output_tokens,
    )


__all__ = ["build_compact_request", "build_prompt_request", "parse_response"]
