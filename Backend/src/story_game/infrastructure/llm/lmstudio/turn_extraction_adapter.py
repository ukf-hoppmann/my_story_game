"""LM Studio structured-output adapter for one turn's change proposal."""

from __future__ import annotations

from typing import Protocol

from pydantic import ValidationError as PydanticError

from story_game.application import Failure, Success
from story_game.application.llm import (
    LLMError,
    LLMErrorKind,
    LLMGenerationCall,
    TurnExtractionPort,
    TurnExtractionRequest,
)

from ..openai_compatible import ChatRequest, ChatResponse, TransportError, to_llm_error
from ..openai_compatible.turn_extraction_wire import build_request, parse_response


class LmStudioExtractionClient(Protocol):
    def complete(self, request: ChatRequest) -> ChatResponse: ...


class LmStudioTurnExtractionAdapter(TurnExtractionPort):
    """Request strict JSON and return only validated application candidates."""

    def __init__(self, client: LmStudioExtractionClient) -> None:
        self._client = client

    def extract(self, call: LLMGenerationCall[TurnExtractionRequest]):
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
            return Success(parse_response(call, response.text))
        except (PydanticError, ValueError):
            return Failure(
                LLMError(
                    LLMErrorKind.INVALID_RESPONSE,
                    "LM Studio hat keinen gültigen Änderungsvorschlag geliefert.",
                )
            )
