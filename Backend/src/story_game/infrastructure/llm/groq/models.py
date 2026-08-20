"""Internal wire values for Groq's OpenAI-compatible chat endpoint."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GroqChatMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class GroqJsonSchema:
    """OpenAI-compatible strict schema requested from Groq."""

    name: str
    strict: bool
    schema: dict[str, Any]

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise ValueError("Ein Groq-JSON-Schema benötigt einen Namen")
        object.__setattr__(self, "name", name)


@dataclass(frozen=True, slots=True)
class GroqChatRequest:
    model: str
    messages: tuple[GroqChatMessage, ...]
    temperature: float | None
    max_tokens: int | None
    response_format: GroqJsonSchema | None = None


@dataclass(frozen=True, slots=True)
class GroqChatResponse:
    text: str
    finish_reason: str | None
