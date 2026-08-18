"""Private LM Studio transport failures translated by the provider adapter."""

from __future__ import annotations

from enum import StrEnum


class LmStudioErrorKind(StrEnum):
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    RATE_LIMITED = "rate_limited"
    MODEL_UNAVAILABLE = "model_unavailable"
    INVALID_REQUEST = "invalid_request"
    CONTEXT_LIMIT = "context_limit"
    INCOMPLETE = "incomplete"
    INVALID_RESPONSE = "invalid_response"


class LmStudioClientError(Exception):
    """An internal transport or wire-format failure."""

    def __init__(self, kind: LmStudioErrorKind, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.retryable = retryable
