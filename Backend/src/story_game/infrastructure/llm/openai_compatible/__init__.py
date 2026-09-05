"""Shared transport, wire types, and task-specific mapping for every
OpenAI-compatible chat completions provider (LM Studio, Groq, Gemini, ...).
"""

from .client import OpenAiCompatibleClient, OpenAiCompatibleSettings
from .error_mapping import to_llm_error
from .errors import TransportError, TransportErrorKind
from .models import ChatMessage, ChatRequest, ChatResponse, JsonSchema

__all__ = [
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "JsonSchema",
    "OpenAiCompatibleClient",
    "OpenAiCompatibleSettings",
    "TransportError",
    "TransportErrorKind",
    "to_llm_error",
]
