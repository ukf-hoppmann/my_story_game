"""Application adapter for LM Studio rolling-summary calls."""

from __future__ import annotations

from typing import Protocol

from story_game.application import Failure, Success
from story_game.application.llm import (
    LLMError,
    LLMErrorKind,
    LLMGenerationCall,
    StorySummaryPort,
    StorySummaryRequest,
    StorySummaryText,
)

from .adapter import _map_error
from .errors import LmStudioClientError
from .models import LmStudioChatMessage, LmStudioChatRequest, LmStudioChatResponse


class LmStudioSummaryClient(Protocol):
    def complete(self, request: LmStudioChatRequest) -> LmStudioChatResponse: ...


class LmStudioStorySummaryAdapter(StorySummaryPort):
    """Translate the summary boundary into LM Studio chat messages."""

    def __init__(self, client: LmStudioSummaryClient) -> None:
        self._client = client

    def summarize(self, call: LLMGenerationCall[StorySummaryRequest]):
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
            return Success(StorySummaryText(response.text))
        except ValueError:
            return Failure(
                LLMError(
                    LLMErrorKind.INVALID_RESPONSE,
                    "LM Studio hat keine gültige Zusammenfassung geliefert.",
                )
            )


def _messages_for(request: StorySummaryRequest) -> tuple[LmStudioChatMessage, ...]:
    sections = [
        "[language]\n" + request.language,
        "[previous_summary]\n"
        + (request.previous_summary or "Es gibt noch keine Zusammenfassung."),
        "[player_input]\n" + request.player_input,
        "[narration]\n" + request.narration,
    ]
    return (
        LmStudioChatMessage(role="system", content="\n\n".join(request.system_prompts)),
        LmStudioChatMessage(role="user", content="\n\n".join(sections)),
    )
