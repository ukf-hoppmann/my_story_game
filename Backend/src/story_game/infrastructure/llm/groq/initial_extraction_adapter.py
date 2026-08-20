"""Groq structured-output adapter for initial WorldState extraction."""

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


class GroqExtractionClient(Protocol):
    def complete(self, request: ChatRequest) -> ChatResponse: ...


class GroqInitialWorldExtractionAdapter(InitialWorldExtractionPort):
    """Request strict JSON and return only validated application candidates."""

    def __init__(self, client: GroqExtractionClient) -> None:
        self._client = client

    def extract(self, call: LLMGenerationCall[InitialWorldExtractionRequest]):
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
            return Success(parse_response(response.text))
        except (PydanticError, ValueError):
            return Failure(
                LLMError(
                    LLMErrorKind.INVALID_RESPONSE,
                    "Groq hat keinen gültigen Initial-WorldState-Candidate geliefert.",
                )
            )
