"""Internal wire values for LM Studio's OpenAI-compatible chat endpoint."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LmStudioChatMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class LmStudioChatRequest:
    model: str
    messages: tuple[LmStudioChatMessage, ...]
    temperature: float | None
    max_tokens: int | None


@dataclass(frozen=True, slots=True)
class LmStudioChatResponse:
    text: str
    finish_reason: str | None
