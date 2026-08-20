"""Application adapter for Groq rolling-summary calls."""

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
from .errors import GroqClientError
from .models import GroqChatMessage, GroqChatRequest, GroqChatResponse


class GroqSummaryClient(Protocol):
    def complete(self, request: GroqChatRequest) -> GroqChatResponse: ...


class GroqStorySummaryAdapter(StorySummaryPort):
    """Translate the summary boundary into Groq chat messages."""

    def __init__(self, client: GroqSummaryClient) -> None:
        self._client = client

    def summarize(self, call: LLMGenerationCall[StorySummaryRequest]):
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
            return Success(StorySummaryText(response.text))
        except ValueError:
            return Failure(
                LLMError(
                    LLMErrorKind.INVALID_RESPONSE,
                    "Groq hat keine gültige Zusammenfassung geliefert.",
                )
            )


def _messages_for(request: StorySummaryRequest) -> tuple[GroqChatMessage, ...]:
    sections = [
        "[language]\n" + request.language,
        "[previous_summary]\n"
        + (request.previous_summary or "Es gibt noch keine Zusammenfassung."),
        "[player_input]\n" + request.player_input,
        "[narration]\n" + request.narration,
    ]
    return (
        GroqChatMessage(role="system", content="\n\n".join(request.system_prompts)),
        GroqChatMessage(role="user", content="\n\n".join(sections)),
    )
