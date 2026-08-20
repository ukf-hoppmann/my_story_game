from __future__ import annotations

import json

import httpx
import pytest

from story_game.infrastructure.llm.groq.client import GroqClient, GroqSettings
from story_game.infrastructure.llm.groq.errors import GroqClientError, GroqErrorKind
from story_game.infrastructure.llm.groq.models import (
    GroqChatMessage,
    GroqChatRequest,
    GroqJsonSchema,
)


def request() -> GroqChatRequest:
    return GroqChatRequest(
        model="llama-3.3-70b-versatile",
        messages=(GroqChatMessage("user", "Hallo"),),
        temperature=0.0,
        max_tokens=16,
        response_format=GroqJsonSchema(
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


def test_settings_require_a_non_empty_api_key() -> None:
    with pytest.raises(ValueError, match="API-Key"):
        GroqSettings("https://api.groq.com/openai/v1", api_token=None)


def test_settings_default_to_the_groq_base_url() -> None:
    settings = GroqSettings(api_token="secret")

    assert settings.base_url == "https://api.groq.com/openai/v1"


def test_constructing_the_client_never_requires_a_key_up_front() -> None:
    """Composition Root can always build a GroqClient, even before

    configs/llm.secrets.toml exists, as long as Groq is never actually
    called for a task — otherwise app startup would fail whenever a Groq
    key isn't configured yet, even for setups that never use Groq.
    """
    client = GroqClient(lambda: GroqSettings(api_token=None))
    client.close()


def test_complete_translates_a_missing_key_into_a_typed_authentication_error() -> None:
    client = GroqClient(lambda: GroqSettings(api_token=None))

    with pytest.raises(GroqClientError) as failure:
        client.complete(request())

    assert failure.value.kind == GroqErrorKind.AUTHENTICATION
    client.close()


def test_client_posts_openai_compatible_payload_with_bearer_auth() -> None:
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
    http_client = httpx.Client(transport=transport, base_url="https://groq.test/v1/")
    client = GroqClient(
        GroqSettings("https://groq.test/v1", api_token="secret"),
        http_client=http_client,
    )

    response = client.complete(request())

    assert response.text == "Antwort"
    assert observed["url"] == "https://groq.test/v1/chat/completions"
    assert observed["authorization"] == "Bearer secret"
    assert observed["payload"]["model"] == "llama-3.3-70b-versatile"  # type: ignore[index]
    http_client.close()


def test_client_reresolves_settings_on_every_call() -> None:
    """Rotating configs/llm.secrets.toml takes effect without a restart."""

    calls: list[str | None] = []

    def handler(incoming: httpx.Request) -> httpx.Response:
        calls.append(incoming.headers.get("authorization"))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": "Antwort"}, "finish_reason": "stop"}
                ]
            },
        )

    tokens = iter(["first", "second"])
    http_client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://groq.test/v1/"
    )
    client = GroqClient(
        lambda: GroqSettings("https://groq.test/v1", api_token=next(tokens)),
        http_client=http_client,
    )

    client.complete(request())
    client.complete(request())

    assert calls == ["Bearer first", "Bearer second"]
    http_client.close()


@pytest.mark.parametrize(
    ("status_code", "kind"),
    [
        (401, GroqErrorKind.AUTHENTICATION),
        (404, GroqErrorKind.MODEL_UNAVAILABLE),
        (413, GroqErrorKind.CONTEXT_LIMIT),
        (429, GroqErrorKind.RATE_LIMITED),
        (500, GroqErrorKind.UNAVAILABLE),
    ],
)
def test_client_maps_relevant_http_statuses(status_code: int, kind: GroqErrorKind) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(status_code, text="provider detail"))
    http_client = httpx.Client(transport=transport, base_url="https://groq.test/v1/")
    client = GroqClient(
        GroqSettings("https://groq.test/v1", api_token="secret"), http_client=http_client
    )

    with pytest.raises(GroqClientError) as failure:
        client.complete(request())

    assert failure.value.kind == kind
    http_client.close()


def test_client_rejects_invalid_wire_response() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"choices": []}))
    http_client = httpx.Client(transport=transport, base_url="https://groq.test/v1/")
    client = GroqClient(
        GroqSettings("https://groq.test/v1", api_token="secret"), http_client=http_client
    )

    with pytest.raises(GroqClientError) as failure:
        client.complete(request())

    assert failure.value.kind == GroqErrorKind.INVALID_RESPONSE
    http_client.close()
