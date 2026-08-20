"""Gemini structured-output adapter for initial WorldState extraction."""

from __future__ import annotations

from typing import Protocol

from pydantic import ValidationError as PydanticError

from story_game.application import Failure, Success
from story_game.application.llm import (
    InitialWorldExtractionPort,
    InitialWorldExtractionRequest,
    LLMError,
    LLMErrorKind,
    LLMGenerationCall,
)

from ..openai_compatible import ChatRequest, ChatResponse, TransportError, to_llm_error
from ..openai_compatible.initial_extraction_wire import build_request, parse_response


class GeminiExtractionClient(Protocol):
    def complete(self, request: ChatRequest) -> ChatResponse: ...


class GeminiInitialWorldExtractionAdapter(InitialWorldExtractionPort):
    """Request strict JSON and return only validated application candidates."""

    def __init__(self, client: GeminiExtractionClient) -> None:
        self._client = client

    def extract(self, call: LLMGenerationCall[InitialWorldExtractionRequest]):
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
            return Success(parse_response(response.text))
        except (PydanticError, ValueError):
            return Failure(
                LLMError(
                    LLMErrorKind.INVALID_RESPONSE,
                    "Gemini hat keinen gültigen Initial-WorldState-Candidate geliefert.",
                )
            )
