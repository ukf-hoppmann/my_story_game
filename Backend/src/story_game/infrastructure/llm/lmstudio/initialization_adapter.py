"""LM Studio adapter for the provider-independent story-initialization port."""

from __future__ import annotations

from typing import Protocol

from story_game.application import Failure, Success
from story_game.application.llm import (
    LLMError,
    LLMErrorKind,
    LLMGenerationCall,
    StoryInitializationPort,
    StoryInitializationRequest,
)

from ..openai_compatible import ChatRequest, ChatResponse, TransportError, to_llm_error
from ..openai_compatible.story_initialization_wire import build_request, parse_response


class LmStudioInitializationClient(Protocol):
    """The narrow completion surface used by the opening adapter."""

    def complete(self, request: ChatRequest) -> ChatResponse: ...


class LmStudioStoryInitializationAdapter(StoryInitializationPort):
    """Render a prepared opening request without selecting any game context."""

    def __init__(self, client: LmStudioInitializationClient) -> None:
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
            response = self._client.complete(build_request(call))
        except TransportError as error:
            return Failure(to_llm_error(error))
        try:
            return Success(parse_response(response))
        except ValueError:
            return Failure(
                LLMError(
                    LLMErrorKind.INVALID_RESPONSE,
                    "LM Studio hat keine gültige Eröffnungsprosa geliefert.",
                )
            )
