"""Application adapter for Gemini rolling-summary calls."""

from __future__ import annotations

from typing import Protocol

from story_game.application import Failure, Success
from story_game.application.llm import (
    LLMError,
    LLMErrorKind,
    LLMGenerationCall,
    StorySummaryPort,
    StorySummaryRequest,
)

from ..openai_compatible import ChatRequest, ChatResponse, TransportError, to_llm_error
from ..openai_compatible.summary_wire import build_request, parse_response


class GeminiSummaryClient(Protocol):
    def complete(self, request: ChatRequest) -> ChatResponse: ...


class GeminiStorySummaryAdapter(StorySummaryPort):
    """Translate the summary boundary into Gemini chat messages."""

    def __init__(self, client: GeminiSummaryClient) -> None:
        self._client = client

    def summarize(self, call: LLMGenerationCall[StorySummaryRequest]):
        if call.model_selection.provider_id != "gemini":
            return Failure(
                LLMError(
                    LLMErrorKind.CONFIGURATION,
                    "Der Gemini-Adapter wurde mit einem anderen Provider aufgerufen.",
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
                    "Gemini hat keine gültige Zusammenfassung geliefert.",
                )
            )
