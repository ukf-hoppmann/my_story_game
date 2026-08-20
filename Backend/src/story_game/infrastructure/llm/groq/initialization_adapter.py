"""Groq adapter for the provider-independent story-initialization port."""

from __future__ import annotations

from typing import Protocol

from story_game.application import Failure, Success
from story_game.application.llm import (
    InitialStoryText,
    LLMError,
    LLMErrorKind,
    LLMGenerationCall,
    StoryInitializationPort,
    StoryInitializationRequest,
)

from .adapter import _map_error
from .client import GroqClient
from .errors import GroqClientError
from .models import GroqChatMessage, GroqChatRequest, GroqChatResponse


class GroqInitializationClient(Protocol):
    """The narrow completion surface used by the opening adapter."""

    def complete(self, request: GroqChatRequest) -> GroqChatResponse: ...


class GroqStoryInitializationAdapter(StoryInitializationPort):
    """Render a prepared opening request without selecting any game context."""

    def __init__(self, client: GroqInitializationClient | GroqClient) -> None:
        self._client = client

    def generate(self, call: LLMGenerationCall[StoryInitializationRequest]):
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
            return Success(InitialStoryText(response.text))
        except ValueError:
            return Failure(
                LLMError(
                    LLMErrorKind.INVALID_RESPONSE,
                    "Groq hat keine gültige Eröffnungsprosa geliefert.",
                )
            )


def _messages_for(request: StoryInitializationRequest) -> tuple[GroqChatMessage, ...]:
    sections = [
        "[configuration]\n" + request.configuration,
        "[initial_prompt]\n" + request.initial_prompt,
    ]
    if request.controllable_characters:
        lines = [
            f"- Name: {character.name}\n"
            f"  Beschreibung: {character.description or 'Keine zusätzliche Beschreibung.'}"
            for character in request.controllable_characters
        ]
        sections.append("[controllable_characters]\n" + "\n".join(lines))
    return (
        GroqChatMessage(role="system", content="\n\n".join(request.system_prompts)),
        GroqChatMessage(
            role="user",
            content="\n\n".join(sections),
        ),
    )
