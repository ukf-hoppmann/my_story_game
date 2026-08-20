"""Application adapter for Groq story-generation calls."""

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

from .client import GroqClient
from .errors import GroqClientError, GroqErrorKind
from .models import GroqChatMessage, GroqChatRequest, GroqChatResponse


class GroqCompletionClient(Protocol):
    """The small client surface required by the provider adapter."""

    def complete(self, request: GroqChatRequest) -> GroqChatResponse: ...


class GroqStoryGenerationAdapter(StoryGenerationPort):
    """Translate the stable story boundary into Groq chat messages."""

    def __init__(self, client: GroqCompletionClient | GroqClient) -> None:
        self._client = client

    def generate(self, call: LLMGenerationCall[StoryGenerationRequest]):
        if call.model_selection.provider_id != "groq":
            return Failure(
                LLMError(
                    LLMErrorKind.CONFIGURATION,
                    "Der Groq-Adapter wurde mit einem anderen Provider aufgerufen.",
                )
            )

        try:
            response = self._client.complete(
                GroqChatRequest(
                    model=call.model_selection.model_id,
                    messages=_messages_for(call.request),
                    temperature=call.generation_options.temperature,
                    max_tokens=call.generation_options.max_output_tokens,
                )
            )
        except GroqClientError as error:
            return Failure(_map_error(error))

        try:
            return Success(StoryGenerationData(response.text))
        except ValueError:
            return Failure(
                LLMError(
                    LLMErrorKind.INVALID_RESPONSE,
                    "Groq hat keine gültige Story-Prosa geliefert.",
                )
            )


def _messages_for(request: StoryGenerationRequest) -> tuple[GroqChatMessage, ...]:
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
        GroqChatMessage(role="system", content=system_prompt),
        GroqChatMessage(role="user", content=context),
    )


def _map_error(error: GroqClientError) -> LLMError:
    kind_map = {
        GroqErrorKind.UNAVAILABLE: LLMErrorKind.UNAVAILABLE,
        GroqErrorKind.TIMEOUT: LLMErrorKind.TIMEOUT,
        GroqErrorKind.AUTHENTICATION: LLMErrorKind.AUTHENTICATION,
        GroqErrorKind.RATE_LIMITED: LLMErrorKind.RATE_LIMITED,
        GroqErrorKind.MODEL_UNAVAILABLE: LLMErrorKind.MODEL_UNAVAILABLE,
        GroqErrorKind.INVALID_REQUEST: LLMErrorKind.INVALID_REQUEST,
        GroqErrorKind.CONTEXT_LIMIT: LLMErrorKind.CONTEXT_LIMIT,
        GroqErrorKind.INCOMPLETE: LLMErrorKind.INCOMPLETE,
        GroqErrorKind.INVALID_RESPONSE: LLMErrorKind.INVALID_RESPONSE,
    }
    return LLMError(kind_map[error.kind], error.message, retryable=error.retryable)
