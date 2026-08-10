"""LM Studio adapter for the provider-independent story-initialization port."""

from __future__ import annotations

from typing import Protocol

from story_game.application import Failure, Success
from story_game.application.llm import (
    InitialStoryText,
    LLMError,
    LLMErrorKind,
    LLMGenerationCall,
    StoryInitializationPort,
    StoryInitializationRequest,
)

from .adapter import _map_error
from .client import LmStudioClient
from .errors import LmStudioClientError
from .models import LmStudioChatMessage, LmStudioChatRequest, LmStudioChatResponse


class LmStudioInitializationClient(Protocol):
    """The narrow completion surface used by the opening adapter."""

    def complete(self, request: LmStudioChatRequest) -> LmStudioChatResponse: ...


class LmStudioStoryInitializationAdapter(StoryInitializationPort):
    """Render a prepared opening request without selecting any game context."""

    def __init__(self, client: LmStudioInitializationClient | LmStudioClient) -> None:
        self._client = client

    def generate(self, call: LLMGenerationCall[StoryInitializationRequest]):
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
                )
            )
        except LmStudioClientError as error:
            return Failure(_map_error(error))
        try:
            return Success(InitialStoryText(response.text))
        except ValueError:
            return Failure(
                LLMError(
                    LLMErrorKind.INVALID_RESPONSE,
                    "LM Studio hat keine gültige Eröffnungsprosa geliefert.",
                )
            )


def _messages_for(request: StoryInitializationRequest) -> tuple[LmStudioChatMessage, ...]:
    return (
        LmStudioChatMessage(role="system", content="\n\n".join(request.system_prompts)),
        LmStudioChatMessage(
            role="user",
            content="\n\n".join(
                (
                    "[configuration]\n" + request.configuration,
                    "[initial_prompt]\n" + request.initial_prompt,
                )
            ),
        ),
    )
