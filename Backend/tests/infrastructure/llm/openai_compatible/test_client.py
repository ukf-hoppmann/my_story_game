from __future__ import annotations

import json
import logging

import httpx
import pytest
import structlog
from structlog.testing import LogCapture

from story_game.infrastructure.llm.openai_compatible.client import (
    OpenAiCompatibleClient,
    OpenAiCompatibleSettings,
)
from story_game.infrastructure.llm.openai_compatible.errors import (
    TransportError,
    TransportErrorKind,
)
from story_game.infrastructure.llm.openai_compatible.models import (
    ChatMessage,
    ChatRequest,
    JsonSchema,
)


def request() -> ChatRequest:
    return ChatRequest(
        model="local/story-model",
        messages=(ChatMessage("user", "Hallo"),),
        temperature=0.0,
        max_tokens=16,
        response_format=JsonSchema(
            name="answer",
            strict=True,
            schema={
                "type": "object",
                "properties": {"answer": {"type": "string"}},
                "required": ["answer"],
                "additionalProperties": False,
            },
        ),
    )


def test_client_posts_openai_compatible_payload_and_parses_response() -> None:
    observed: dict[str, object] = {}

    def handler(incoming: httpx.Request) -> httpx.Response:
        observed["url"] = str(incoming.url)
        observed["authorization"] = incoming.headers.get("authorization")
        observed["payload"] = json.loads(incoming.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": "Antwort"}, "finish_reason": "stop"}
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="http://provider.test/v1/")
    client = OpenAiCompatibleClient(
        OpenAiCompatibleSettings("http://provider.test/v1", api_token="secret"),
        http_client=http_client,
    )

    response = client.complete(request())

    assert response.text == "Antwort"
    assert observed["url"] == "http://provider.test/v1/chat/completions"
    assert observed["authorization"] == "Bearer secret"
    assert observed["payload"]["model"] == "local/story-model"  # type: ignore[index]
    assert observed["payload"]["response_format"] == {  # type: ignore[index]
        "type": "json_schema",
        "json_schema": {
            "name": "answer",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {"answer": {"type": "string"}},
                "required": ["answer"],
                "additionalProperties": False,
            },
        },
    }
    http_client.close()


def test_client_omits_authorization_header_without_a_token() -> None:
    observed: dict[str, object] = {}

    def handler(incoming: httpx.Request) -> httpx.Response:
        observed["authorization"] = incoming.headers.get("authorization")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "Antwort"}, "finish_reason": "stop"}]},
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://provider.test/v1/")
    client = OpenAiCompatibleClient(
        OpenAiCompatibleSettings("http://provider.test/v1"), http_client=http_client
    )

    client.complete(request())

    assert observed["authorization"] is None
    http_client.close()


def _capture() -> LogCapture:
    capture = LogCapture()
    structlog.configure(
        processors=[capture],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
    )
    return capture


def _handler(incoming: httpx.Request) -> httpx.Response:
    del incoming
    return httpx.Response(
        200,
        json={"choices": [{"message": {"role": "assistant", "content": "Antwort"}, "finish_reason": "stop"}]},
    )


def test_debug_mode_logs_the_full_request_payload_and_raw_response() -> None:
    capture = _capture()
    http_client = httpx.Client(
        transport=httpx.MockTransport(_handler), base_url="http://provider.test/v1/"
    )
    client = OpenAiCompatibleClient(
        OpenAiCompatibleSettings("http://provider.test/v1"),
        http_client=http_client,
        debug_enabled=True,
    )

    client.complete(request())

    events = [entry["event"] for entry in capture.entries]
    assert "openai_compatible.request" in events
    assert "openai_compatible.raw_response" in events
    request_entry = next(e for e in capture.entries if e["event"] == "openai_compatible.request")
    assert request_entry["payload"]["model"] == "local/story-model"
    http_client.close()


def test_default_profile_never_logs_the_request_or_response() -> None:
    capture = _capture()
    http_client = httpx.Client(
        transport=httpx.MockTransport(_handler), base_url="http://provider.test/v1/"
    )
    client = OpenAiCompatibleClient(
        OpenAiCompatibleSettings("http://provider.test/v1"), http_client=http_client
    )

    client.complete(request())

    assert capture.entries == []
    http_client.close()


def test_constructing_the_client_never_resolves_settings_up_front() -> None:
    """A provider settings factory that requires a not-yet-configured token

    (Groq, Gemini) must not fail Composition Root startup merely because the
    client was constructed — only when it is actually called.
    """

    def resolve_settings() -> OpenAiCompatibleSettings:
        raise ValueError("kein Key konfiguriert")

    client = OpenAiCompatibleClient(resolve_settings)
    client.close()


def test_complete_translates_a_settings_value_error_into_a_typed_authentication_error() -> None:
    def resolve_settings() -> OpenAiCompatibleSettings:
        raise ValueError("kein Key konfiguriert")

    client = OpenAiCompatibleClient(resolve_settings)

    with pytest.raises(TransportError) as failure:
        client.complete(request())

    assert failure.value.kind == TransportErrorKind.AUTHENTICATION
    client.close()


def test_client_reresolves_settings_on_every_call() -> None:
    calls: list[str | None] = []

    def handler(incoming: httpx.Request) -> httpx.Response:
        calls.append(incoming.headers.get("authorization"))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "Antwort"}, "finish_reason": "stop"}]},
        )

    tokens = iter(["first", "second"])
    http_client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://provider.test/v1/")
    client = OpenAiCompatibleClient(
        lambda: OpenAiCompatibleSettings("http://provider.test/v1", api_token=next(tokens)),
        http_client=http_client,
    )

    client.complete(request())
    client.complete(request())

    assert calls == ["Bearer first", "Bearer second"]
    http_client.close()


@pytest.mark.parametrize(
    ("status_code", "kind"),
    [
        (401, TransportErrorKind.AUTHENTICATION),
        (404, TransportErrorKind.MODEL_UNAVAILABLE),
        (413, TransportErrorKind.CONTEXT_LIMIT),
        (429, TransportErrorKind.RATE_LIMITED),
        (500, TransportErrorKind.UNAVAILABLE),
    ],
)
def test_client_maps_relevant_http_statuses(status_code: int, kind: TransportErrorKind) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(status_code, text="provider detail"))
    http_client = httpx.Client(transport=transport, base_url="http://provider.test/v1/")
    client = OpenAiCompatibleClient(
        OpenAiCompatibleSettings("http://provider.test/v1"), http_client=http_client
    )

    with pytest.raises(TransportError) as failure:
        client.complete(request())

    assert failure.value.kind == kind
    http_client.close()


def test_client_rejects_invalid_wire_response() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"choices": []}))
    http_client = httpx.Client(transport=transport, base_url="http://provider.test/v1/")
    client = OpenAiCompatibleClient(
        OpenAiCompatibleSettings("http://provider.test/v1"), http_client=http_client
    )

    with pytest.raises(TransportError) as failure:
        client.complete(request())

    assert failure.value.kind == TransportErrorKind.INVALID_RESPONSE
    http_client.close()
