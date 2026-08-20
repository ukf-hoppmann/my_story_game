"""HTTP client for LM Studio's OpenAI-compatible chat completions API."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog

from .errors import LmStudioClientError, LmStudioErrorKind
from .models import LmStudioChatRequest, LmStudioChatResponse

_logger = structlog.get_logger("story_game.lmstudio")


@dataclass(frozen=True, slots=True)
class LmStudioSettings:
    """Runtime-only LM Studio connection settings."""

    base_url: str = "http://localhost:1234/v1"
    api_token: str | None = field(default=None, repr=False)
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        base_url = self.base_url.strip().rstrip("/")
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("LM-Studio-Base-URL muss eine HTTP- oder HTTPS-URL sein")
        if self.timeout_seconds <= 0:
            raise ValueError("Der LM-Studio-Timeout muss positiv sein")
        object.__setattr__(self, "base_url", base_url)
        if self.api_token is not None:
            token = self.api_token.strip()
            object.__setattr__(self, "api_token", token or None)

class LmStudioClient:
    """Perform transport and wire parsing without exposing HTTP to the application."""

    def __init__(
        self,
        settings: LmStudioSettings | Callable[[], LmStudioSettings],
        *,
        http_client: httpx.Client | None = None,
        debug_enabled: bool = False,
    ) -> None:
        self._resolve_settings = settings if callable(settings) else (lambda: settings)
        self._owns_client = http_client is None
        if http_client is not None:
            self._http_client = http_client
        else:
            initial_settings = self._resolve_settings()
            self._http_client = httpx.Client(
                base_url=f"{initial_settings.base_url}/",
                timeout=initial_settings.timeout_seconds,
            )
        self._debug_enabled = debug_enabled

    def close(self) -> None:
        """Close the internally owned HTTP client."""

        if self._owns_client:
            self._http_client.close()

    def complete(self, request: LmStudioChatRequest) -> LmStudioChatResponse:
        settings = self._resolve_settings()
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
            _logger.debug("lmstudio.request", payload=payload)

        try:
            response = self._http_client.post("chat/completions", json=payload, headers=headers)
        except httpx.TimeoutException as error:
            if self._debug_enabled:
                _logger.debug("lmstudio.transport_error", kind="timeout")
            raise LmStudioClientError(
                LmStudioErrorKind.TIMEOUT,
                "Die Verbindung zu LM Studio hat das Zeitlimit überschritten.",
                retryable=True,
            ) from error
        except httpx.HTTPError as error:
            if self._debug_enabled:
                _logger.debug("lmstudio.transport_error", kind="unavailable")
            raise LmStudioClientError(
                LmStudioErrorKind.UNAVAILABLE,
                "LM Studio ist nicht erreichbar.",
                retryable=True,
            ) from error

        if self._debug_enabled:
            _logger.debug(
                "lmstudio.raw_response",
                status_code=response.status_code,
                body=response.text,
            )

        if response.status_code >= 400:
            raise _error_for_status(response.status_code, response.text)

        try:
            document = response.json()
        except ValueError as error:
            raise LmStudioClientError(
                LmStudioErrorKind.INVALID_RESPONSE,
                "LM Studio hat kein gültiges JSON geliefert.",
            ) from error

        return _parse_response(document)


def _error_for_status(status_code: int, response_text: str) -> LmStudioClientError:
    del response_text
    if status_code in {401, 403}:
        return LmStudioClientError(
            LmStudioErrorKind.AUTHENTICATION,
            "LM Studio hat die Anfrage nicht authentifiziert.",
        )
    if status_code == 404:
        return LmStudioClientError(
            LmStudioErrorKind.MODEL_UNAVAILABLE,
            "Das konfigurierte LM-Studio-Modell oder der Endpoint ist nicht verfügbar.",
        )
    if status_code == 429:
        return LmStudioClientError(
            LmStudioErrorKind.RATE_LIMITED,
            "LM Studio hat die Anfrage wegen einer Begrenzung abgelehnt.",
            retryable=True,
        )
    if status_code in {408, 504}:
        return LmStudioClientError(
            LmStudioErrorKind.TIMEOUT,
            "LM Studio hat die Anfrage nicht rechtzeitig verarbeitet.",
            retryable=True,
        )
    if status_code >= 500:
        return LmStudioClientError(
            LmStudioErrorKind.UNAVAILABLE,
            "LM Studio hat einen internen Serverfehler gemeldet.",
            retryable=True,
        )
    if status_code == 413:
        return LmStudioClientError(
            LmStudioErrorKind.CONTEXT_LIMIT,
            "Die LM-Studio-Anfrage überschreitet das Kontextlimit.",
        )
    return LmStudioClientError(
        LmStudioErrorKind.INVALID_REQUEST,
        "LM Studio hat die Anfrage abgelehnt.",
    )


def _parse_response(document: object) -> LmStudioChatResponse:
    if not isinstance(document, dict):
        raise LmStudioClientError(
            LmStudioErrorKind.INVALID_RESPONSE,
            "Die LM-Studio-Antwort hat keine Objektstruktur.",
        )
    choices = document.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise LmStudioClientError(
            LmStudioErrorKind.INVALID_RESPONSE,
            "Die LM-Studio-Antwort enthält keine Auswahl.",
        )
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise LmStudioClientError(
            LmStudioErrorKind.INVALID_RESPONSE,
            "Die LM-Studio-Antwort enthält keinen Textinhalt.",
        )
    text = message["content"].strip()
    if not text:
        raise LmStudioClientError(
            LmStudioErrorKind.INVALID_RESPONSE,
            "LM Studio hat eine leere Antwort geliefert.",
        )
    finish_reason = choice.get("finish_reason")
    if finish_reason == "length":
        raise LmStudioClientError(
            LmStudioErrorKind.INCOMPLETE,
            "LM Studio hat die Antwort am Ausgabelimit abgeschnitten.",
        )
    return LmStudioChatResponse(text=text, finish_reason=finish_reason)
