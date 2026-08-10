"""Internal wire values for LM Studio's OpenAI-compatible chat endpoint."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class LmStudioChatMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class LmStudioJsonSchema:
    """OpenAI-compatible strict schema requested from LM Studio."""

    name: str
    strict: bool
    schema: dict[str, Any]

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise ValueError("Ein LM-Studio-JSON-Schema benötigt einen Namen")
        object.__setattr__(self, "name", name)


@dataclass(frozen=True, slots=True)
class LmStudioChatRequest:
    model: str
    messages: tuple[LmStudioChatMessage, ...]
    temperature: float | None
    max_tokens: int | None
    response_format: LmStudioJsonSchema | None = None


@dataclass(frozen=True, slots=True)
class LmStudioChatResponse:
    text: str
    finish_reason: str | None
