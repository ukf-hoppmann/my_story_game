"""Internal wire values shared by every OpenAI-compatible chat provider.

LM Studio, Groq, and Gemini (via its OpenAI-compatibility endpoint) all speak
the same ``chat/completions`` wire shape. This module owns that shape once;
provider packages import it instead of redefining it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class JsonSchema:
    """OpenAI-compatible strict schema requested from the provider."""

    name: str
    strict: bool
    schema: dict[str, Any]

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise ValueError("Ein JSON-Schema benötigt einen Namen")
        object.__setattr__(self, "name", name)


@dataclass(frozen=True, slots=True)
class ChatRequest:
    model: str
    messages: tuple[ChatMessage, ...]
    temperature: float | None
    max_tokens: int | None
    response_format: JsonSchema | None = None


@dataclass(frozen=True, slots=True)
class ChatResponse:
    text: str
    finish_reason: str | None


__all__ = ["ChatMessage", "ChatRequest", "ChatResponse", "JsonSchema"]
