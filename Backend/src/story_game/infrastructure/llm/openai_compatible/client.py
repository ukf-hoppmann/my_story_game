"""HTTP client shared by every OpenAI-compatible chat completions provider.

One provider (LM Studio, Groq, Gemini, ...) differs from another only in its
connection settings (base_url, whether an api_token is required, timeout) —
never in how the wire request/response is built or parsed. Provider packages
own their own ``*Settings`` factory (validating provider-specific invariants
such as "Groq requires an api_token") and construct this one client with it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog

from .errors import TransportError, TransportErrorKind
from .models import ChatRequest, ChatResponse

_logger = structlog.get_logger("story_game.openai_compatible")


@dataclass(frozen=True, slots=True)
class OpenAiCompatibleSettings:
    """Runtime-only connection settings for one OpenAI-compatible provider.

    Deliberately does not enforce "api_token is required" itself: LM Studio
    genuinely allows an unset token, while Groq/Gemini do not. That
    provider-specific invariant belongs in each provider's own settings
    factory, not in this shared, generic type.
    """

    base_url: str
    api_token: str | None = field(default=None, repr=False)
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        base_url = self.base_url.strip().rstrip("/")
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Die Provider-Base-URL muss eine HTTP- oder HTTPS-URL sein")
        if self.timeout_seconds <= 0:
            raise ValueError("Der Provider-Timeout muss positiv sein")
        object.__setattr__(self, "base_url", base_url)
        if self.api_token is not None:
            token = self.api_token.strip()
            object.__setattr__(self, "api_token", token or None)


class OpenAiCompatibleClient:
    """Perform transport and wire parsing without exposing HTTP to the application."""

    def __init__(
        self,
        settings: OpenAiCompatibleSettings | Callable[[], OpenAiCompatibleSettings],
        *,
        http_client: httpx.Client | None = None,
        debug_enabled: bool = False,
    ) -> None:
        self._resolve_settings = settings if callable(settings) else (lambda: settings)
        self._owns_client = http_client is None
        if http_client is not None:
            self._http_client = http_client
        else:
            # Deliberately does NOT resolve settings here: a provider whose
            # settings factory requires a not-yet-configured api_token (Groq,
            # Gemini) must not fail Composition Root startup just because it
            # was constructed, only when it is actually called. `complete()`
            # re-resolves and applies the real base_url/timeout/token before
            # every request.
            self._http_client = httpx.Client()
        self._debug_enabled = debug_enabled

    def close(self) -> None:
        """Close the internally owned HTTP client."""

        if self._owns_client:
            self._http_client.close()

    def complete(self, request: ChatRequest) -> ChatResponse:
        try:
            settings = self._resolve_settings()
        except ValueError as error:
            # A provider-specific settings factory raises ValueError for a
            # missing/empty required api_token (e.g. no configs/llm.secrets.toml
            # entry yet). Translate it into the same typed family every other
            # transport failure uses instead of letting a raw ValueError cross
            # the port.
            raise TransportError(TransportErrorKind.AUTHENTICATION, str(error)) from error

        # Re-applying the current connection settings before every request lets
        # provider config (base_url/timeout) be reloaded from disk on each call,
        # matching how task/model selection is already reloaded per invocation.
        self._http_client.base_url = httpx.URL(f"{settings.base_url}/")
        self._http_client.timeout = httpx.Timeout(settings.timeout_seconds)

        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            "stream": False,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.response_format is not None:
            response_format = request.response_format
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": response_format.name,
                    "strict": response_format.strict,
                    "schema": response_format.schema,
                },
            }

        headers = {"Content-Type": "application/json"}
        if settings.api_token:
            headers["Authorization"] = f"Bearer {settings.api_token}"

        if self._debug_enabled:
            _logger.debug("openai_compatible.request", payload=payload)

        try:
            response = self._http_client.post("chat/completions", json=payload, headers=headers)
        except httpx.TimeoutException as error:
            if self._debug_enabled:
                _logger.debug("openai_compatible.transport_error", kind="timeout")
            raise TransportError(
                TransportErrorKind.TIMEOUT,
                "Die Verbindung zum Provider hat das Zeitlimit überschritten.",
                retryable=True,
            ) from error
        except httpx.HTTPError as error:
            if self._debug_enabled:
                _logger.debug("openai_compatible.transport_error", kind="unavailable")
            raise TransportError(
                TransportErrorKind.UNAVAILABLE,
                "Der Provider ist nicht erreichbar.",
                retryable=True,
            ) from error

        if self._debug_enabled:
            _logger.debug(
                "openai_compatible.raw_response",
                status_code=response.status_code,
                body=response.text,
            )

        if response.status_code >= 400:
            raise _error_for_status(response.status_code, response.text)

        try:
            document = response.json()
        except ValueError as error:
            raise TransportError(
                TransportErrorKind.INVALID_RESPONSE,
                "Der Provider hat kein gültiges JSON geliefert.",
            ) from error

        return _parse_response(document)


def _error_for_status(status_code: int, response_text: str) -> TransportError:
    del response_text
    if status_code in {401, 403}:
        return TransportError(
            TransportErrorKind.AUTHENTICATION,
            "Der Provider hat die Anfrage nicht authentifiziert.",
        )
    if status_code == 404:
        return TransportError(
            TransportErrorKind.MODEL_UNAVAILABLE,
            "Das konfigurierte Modell oder der Endpoint ist nicht verfügbar.",
        )
    if status_code == 429:
        return TransportError(
            TransportErrorKind.RATE_LIMITED,
            "Der Provider hat die Anfrage wegen einer Begrenzung abgelehnt.",
            retryable=True,
        )
    if status_code in {408, 504}:
        return TransportError(
            TransportErrorKind.TIMEOUT,
            "Der Provider hat die Anfrage nicht rechtzeitig verarbeitet.",
            retryable=True,
        )
    if status_code >= 500:
        return TransportError(
            TransportErrorKind.UNAVAILABLE,
            "Der Provider hat einen internen Serverfehler gemeldet.",
            retryable=True,
        )
    if status_code == 413:
        return TransportError(
            TransportErrorKind.CONTEXT_LIMIT,
            "Die Anfrage überschreitet das Kontextlimit.",
        )
    return TransportError(
        TransportErrorKind.INVALID_REQUEST,
        "Der Provider hat die Anfrage abgelehnt.",
    )


def _parse_response(document: object) -> ChatResponse:
    if not isinstance(document, dict):
        raise TransportError(
            TransportErrorKind.INVALID_RESPONSE,
            "Die Provider-Antwort hat keine Objektstruktur.",
        )
    choices = document.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise TransportError(
            TransportErrorKind.INVALID_RESPONSE,
            "Die Provider-Antwort enthält keine Auswahl.",
        )
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise TransportError(
            TransportErrorKind.INVALID_RESPONSE,
            "Die Provider-Antwort enthält keinen Textinhalt.",
        )
    text = message["content"].strip()
    if not text:
        raise TransportError(
            TransportErrorKind.INVALID_RESPONSE,
            "Der Provider hat eine leere Antwort geliefert.",
        )
    finish_reason = choice.get("finish_reason")
    if finish_reason == "length":
        raise TransportError(
            TransportErrorKind.INCOMPLETE,
            "Der Provider hat die Antwort am Ausgabelimit abgeschnitten.",
        )
    return ChatResponse(text=text, finish_reason=finish_reason)


__all__ = ["OpenAiCompatibleClient", "OpenAiCompatibleSettings"]
