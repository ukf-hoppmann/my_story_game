"""HTTP client for Groq's OpenAI-compatible chat completions API."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog

from .errors import GroqClientError, GroqErrorKind
from .models import GroqChatRequest, GroqChatResponse

_logger = structlog.get_logger("story_game.groq")


@dataclass(frozen=True, slots=True)
class GroqSettings:
    """Runtime-only Groq connection settings.

    Unlike LM Studio, Groq is a hosted API: every request MUST carry an
    Authorization header, so ``api_token`` is required here, not optional.
    """

    base_url: str = "https://api.groq.com/openai/v1"
    api_token: str | None = field(default=None, repr=False)
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        base_url = self.base_url.strip().rstrip("/")
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Groq-Base-URL muss eine HTTP- oder HTTPS-URL sein")
        if self.timeout_seconds <= 0:
            raise ValueError("Der Groq-Timeout muss positiv sein")
        object.__setattr__(self, "base_url", base_url)
        token = (self.api_token or "").strip()
        if not token:
            raise ValueError(
                "Groq benötigt einen API-Key (aus configs/llm.secrets.toml)"
            )
        object.__setattr__(self, "api_token", token)

class GroqClient:
    """Perform transport and wire parsing without exposing HTTP to the application."""

    def __init__(
        self,
        settings: GroqSettings | Callable[[], GroqSettings],
        *,
        http_client: httpx.Client | None = None,
        debug_enabled: bool = False,
    ) -> None:
        self._resolve_settings = settings if callable(settings) else (lambda: settings)
        self._owns_client = http_client is None
        if http_client is not None:
            self._http_client = http_client
        else:
            # Deliberately does NOT resolve settings here: unlike LM Studio,
            # Groq requires an api_key, which may not exist yet (no
            # configs/llm.secrets.toml) even when no task actually routes to
            # Groq. Building this client must not fail Composition Root
            # startup for that reason — `complete()` re-resolves and applies
            # the real base_url/timeout (and validates the key) before every
            # request, same as LM Studio already does for base_url/timeout.
            self._http_client = httpx.Client()
        self._debug_enabled = debug_enabled

    def close(self) -> None:
        """Close the internally owned HTTP client."""

        if self._owns_client:
            self._http_client.close()

    def complete(self, request: GroqChatRequest) -> GroqChatResponse:
        try:
            settings = self._resolve_settings()
        except ValueError as error:
            # A missing/empty api_key (configs/llm.secrets.toml not set up
            # yet) surfaces as GroqSettings.__post_init__ raising ValueError.
            # Translate it into the same typed family every other transport
            # failure uses instead of letting a raw ValueError cross the port.
            raise GroqClientError(GroqErrorKind.AUTHENTICATION, str(error)) from error
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
            _logger.debug("groq.request", payload=payload)

        try:
            response = self._http_client.post("chat/completions", json=payload, headers=headers)
        except httpx.TimeoutException as error:
            if self._debug_enabled:
                _logger.debug("groq.transport_error", kind="timeout")
            raise GroqClientError(
                GroqErrorKind.TIMEOUT,
                "Die Verbindung zu Groq hat das Zeitlimit überschritten.",
                retryable=True,
            ) from error
        except httpx.HTTPError as error:
            if self._debug_enabled:
                _logger.debug("groq.transport_error", kind="unavailable")
            raise GroqClientError(
                GroqErrorKind.UNAVAILABLE,
                "Groq ist nicht erreichbar.",
                retryable=True,
            ) from error

        if self._debug_enabled:
            _logger.debug(
                "groq.raw_response",
                status_code=response.status_code,
                body=response.text,
            )

        if response.status_code >= 400:
            raise _error_for_status(response.status_code, response.text)

        try:
            document = response.json()
        except ValueError as error:
            raise GroqClientError(
                GroqErrorKind.INVALID_RESPONSE,
                "Groq hat kein gültiges JSON geliefert.",
            ) from error

        return _parse_response(document)


def _error_for_status(status_code: int, response_text: str) -> GroqClientError:
    del response_text
    if status_code in {401, 403}:
        return GroqClientError(
            GroqErrorKind.AUTHENTICATION,
            "Groq hat die Anfrage nicht authentifiziert.",
        )
    if status_code == 404:
        return GroqClientError(
            GroqErrorKind.MODEL_UNAVAILABLE,
            "Das konfigurierte Groq-Modell oder der Endpoint ist nicht verfügbar.",
        )
    if status_code == 429:
        return GroqClientError(
            GroqErrorKind.RATE_LIMITED,
            "Groq hat die Anfrage wegen einer Begrenzung abgelehnt.",
            retryable=True,
        )
    if status_code in {408, 504}:
        return GroqClientError(
            GroqErrorKind.TIMEOUT,
            "Groq hat die Anfrage nicht rechtzeitig verarbeitet.",
            retryable=True,
        )
    if status_code >= 500:
        return GroqClientError(
            GroqErrorKind.UNAVAILABLE,
            "Groq hat einen internen Serverfehler gemeldet.",
            retryable=True,
        )
    if status_code == 413:
        return GroqClientError(
            GroqErrorKind.CONTEXT_LIMIT,
            "Die Groq-Anfrage überschreitet das Kontextlimit.",
        )
    return GroqClientError(
        GroqErrorKind.INVALID_REQUEST,
        "Groq hat die Anfrage abgelehnt.",
    )


def _parse_response(document: object) -> GroqChatResponse:
    if not isinstance(document, dict):
        raise GroqClientError(
            GroqErrorKind.INVALID_RESPONSE,
            "Die Groq-Antwort hat keine Objektstruktur.",
        )
    choices = document.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise GroqClientError(
            GroqErrorKind.INVALID_RESPONSE,
            "Die Groq-Antwort enthält keine Auswahl.",
        )
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise GroqClientError(
            GroqErrorKind.INVALID_RESPONSE,
            "Die Groq-Antwort enthält keinen Textinhalt.",
        )
    text = message["content"].strip()
    if not text:
        raise GroqClientError(
            GroqErrorKind.INVALID_RESPONSE,
            "Groq hat eine leere Antwort geliefert.",
        )
    finish_reason = choice.get("finish_reason")
    if finish_reason == "length":
        raise GroqClientError(
            GroqErrorKind.INCOMPLETE,
            "Groq hat die Antwort am Ausgabelimit abgeschnitten.",
        )
    return GroqChatResponse(text=text, finish_reason=finish_reason)
