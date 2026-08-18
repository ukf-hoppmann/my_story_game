"""Application adapter for LM Studio story-generation calls."""

from __future__ import annotations

from typing import Protocol

from story_game.application import Failure, Success
from story_game.application.llm import (
    LLMError,
    LLMErrorKind,
    LLMGenerationCall,
    StoryGenerationData,
    StoryGenerationPort,
    StoryGenerationRequest,
)

from .client import LmStudioClient
from .errors import LmStudioClientError, LmStudioErrorKind
from .models import LmStudioChatMessage, LmStudioChatRequest, LmStudioChatResponse


class LmStudioCompletionClient(Protocol):
    """The small client surface required by the provider adapter."""

    def complete(self, request: LmStudioChatRequest) -> LmStudioChatResponse: ...


class LmStudioStoryGenerationAdapter(StoryGenerationPort):
    """Translate the stable story boundary into LM Studio chat messages."""

    def __init__(self, client: LmStudioCompletionClient | LmStudioClient) -> None:
        self._client = client

    def generate(self, call: LLMGenerationCall[StoryGenerationRequest]):
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
            return Success(StoryGenerationData(response.text))
        except ValueError:
            return Failure(
                LLMError(
                    LLMErrorKind.INVALID_RESPONSE,
                    "LM Studio hat keine gültige Story-Prosa geliefert.",
                )
            )


def _messages_for(request: StoryGenerationRequest) -> tuple[LmStudioChatMessage, ...]:
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
        LmStudioChatMessage(role="system", content=system_prompt),
        LmStudioChatMessage(role="user", content=context),
    )


def _map_error(error: LmStudioClientError) -> LLMError:
    kind_map = {
        LmStudioErrorKind.UNAVAILABLE: LLMErrorKind.UNAVAILABLE,
        LmStudioErrorKind.TIMEOUT: LLMErrorKind.TIMEOUT,
        LmStudioErrorKind.AUTHENTICATION: LLMErrorKind.AUTHENTICATION,
        LmStudioErrorKind.RATE_LIMITED: LLMErrorKind.RATE_LIMITED,
        LmStudioErrorKind.MODEL_UNAVAILABLE: LLMErrorKind.MODEL_UNAVAILABLE,
        LmStudioErrorKind.INVALID_REQUEST: LLMErrorKind.INVALID_REQUEST,
        LmStudioErrorKind.CONTEXT_LIMIT: LLMErrorKind.CONTEXT_LIMIT,
        LmStudioErrorKind.INCOMPLETE: LLMErrorKind.INCOMPLETE,
        LmStudioErrorKind.INVALID_RESPONSE: LLMErrorKind.INVALID_RESPONSE,
    }
    return LLMError(kind_map[error.kind], error.message, retryable=error.retryable)
