"""Adapters for the scene-image prompt ports over an OpenAI-compatible client.

Every provider speaks the same chat wire shape and differs only in its
``provider_id`` and display name, so one parameterised pair of adapter classes
serves all of them; the composition root builds one per provider and the
routing adapters pick by the call's ``provider_id``.
"""

from __future__ import annotations

from typing import Protocol

from story_game.application import Failure, Success
from story_game.application.llm import (
    CompactImagePromptPort,
    CompactImagePromptRequest,
    LLMError,
    LLMErrorKind,
    LLMGenerationCall,
    SceneImagePromptPort,
    SceneImagePromptRequest,
)

from .error_mapping import to_llm_error
from .errors import TransportError
from .models import ChatRequest, ChatResponse
from .scene_image_wire import (
    build_compact_request,
    build_prompt_request,
    parse_response,
)


class ChatClient(Protocol):
    def complete(self, request: ChatRequest) -> ChatResponse: ...


class _Base:
    def __init__(self, client: ChatClient, provider_id: str, provider_label: str) -> None:
        self._client = client
        self._provider_id = provider_id
        self._provider_label = provider_label

    def _run(self, call: LLMGenerationCall, build):
        if call.model_selection.provider_id != self._provider_id:
            return Failure(
                LLMError(
                    LLMErrorKind.CONFIGURATION,
                    f"Der {self._provider_label}-Adapter wurde mit einem anderen Provider aufgerufen.",
                )
            )
        try:
            response = self._client.complete(build(call))
        except TransportError as error:
            return Failure(to_llm_error(error))
        try:
            return Success(parse_response(response))
        except ValueError:
            return Failure(
                LLMError(
                    LLMErrorKind.INVALID_RESPONSE,
                    f"{self._provider_label} hat keinen gültigen Bildprompt geliefert.",
                )
            )


class OpenAiCompatibleSceneImagePromptAdapter(_Base, SceneImagePromptPort):
    def write(self, call: LLMGenerationCall[SceneImagePromptRequest]):
        return self._run(call, build_prompt_request)


class OpenAiCompatibleCompactImagePromptAdapter(_Base, CompactImagePromptPort):
    def compact(self, call: LLMGenerationCall[CompactImagePromptRequest]):
        return self._run(call, build_compact_request)


__all__ = [
    "OpenAiCompatibleCompactImagePromptAdapter",
    "OpenAiCompatibleSceneImagePromptAdapter",
]
