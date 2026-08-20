"""Translate the shared transport error family into the application boundary.

Identical across every OpenAI-compatible provider — a rate limit, a timeout,
or an invalid response means the same thing regardless of which provider
produced it.
"""

from __future__ import annotations

from story_game.application.llm import LLMError, LLMErrorKind

from .errors import TransportError, TransportErrorKind

_KIND_MAP: dict[TransportErrorKind, LLMErrorKind] = {
    TransportErrorKind.UNAVAILABLE: LLMErrorKind.UNAVAILABLE,
    TransportErrorKind.TIMEOUT: LLMErrorKind.TIMEOUT,
    TransportErrorKind.AUTHENTICATION: LLMErrorKind.AUTHENTICATION,
    TransportErrorKind.RATE_LIMITED: LLMErrorKind.RATE_LIMITED,
    TransportErrorKind.MODEL_UNAVAILABLE: LLMErrorKind.MODEL_UNAVAILABLE,
    TransportErrorKind.INVALID_REQUEST: LLMErrorKind.INVALID_REQUEST,
    TransportErrorKind.CONTEXT_LIMIT: LLMErrorKind.CONTEXT_LIMIT,
    TransportErrorKind.INCOMPLETE: LLMErrorKind.INCOMPLETE,
    TransportErrorKind.INVALID_RESPONSE: LLMErrorKind.INVALID_RESPONSE,
}


def to_llm_error(error: TransportError) -> LLMError:
    return LLMError(_KIND_MAP[error.kind], error.message, retryable=error.retryable)


__all__ = ["to_llm_error"]
