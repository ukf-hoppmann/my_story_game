"""Private transport failures translated by each provider adapter.

Shared across providers: an HTTP-level failure (timeout, auth, rate limit,
...) means the same thing regardless of which OpenAI-compatible provider
produced it.
"""

from __future__ import annotations

from enum import StrEnum


class TransportErrorKind(StrEnum):
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    RATE_LIMITED = "rate_limited"
    MODEL_UNAVAILABLE = "model_unavailable"
    INVALID_REQUEST = "invalid_request"
    CONTEXT_LIMIT = "context_limit"
    INCOMPLETE = "incomplete"
    INVALID_RESPONSE = "invalid_response"


class TransportError(Exception):
    """An internal transport or wire-format failure."""

    def __init__(self, kind: TransportErrorKind, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.retryable = retryable


__all__ = ["TransportError", "TransportErrorKind"]
