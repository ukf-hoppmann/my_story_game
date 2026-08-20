"""Application adapter for Groq story-generation calls."""

from __future__ import annotations

from typing import Protocol

from story_game.application import Failure, Success
from story_game.application.llm import (
    LLMError,
    LLMErrorKind,
    LLMGenerationCall,
    StoryGenerationPort,
    StoryGenerationRequest,
)

from ..openai_compatible import ChatRequest, ChatResponse, TransportError, to_llm_error
from ..openai_compatible.story_generation_wire import build_request, parse_response


class GroqCompletionClient(Protocol):
    """The small client surface required by the provider adapter."""

    def complete(self, request: ChatRequest) -> ChatResponse: ...


class GroqStoryGenerationAdapter(StoryGenerationPort):
    """Translate the stable story boundary into Groq chat messages."""

    def __init__(self, client: GroqCompletionClient) -> None:
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
            response = self._client.complete(build_request(call))
        except TransportError as error:
            return Failure(to_llm_error(error))

        try:
            return Success(parse_response(response))
        except ValueError:
            return Failure(
                LLMError(
                    LLMErrorKind.INVALID_RESPONSE,
                    "Groq hat keine gültige Story-Prosa geliefert.",
                )
            )
