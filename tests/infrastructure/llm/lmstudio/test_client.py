from __future__ import annotations

import json

import httpx
import pytest

from story_game.infrastructure.llm.lmstudio.client import LmStudioClient, LmStudioSettings
from story_game.infrastructure.llm.lmstudio.errors import (
    LmStudioClientError,
    LmStudioErrorKind,
)
from story_game.infrastructure.llm.lmstudio.models import (
    LmStudioChatMessage,
    LmStudioChatRequest,
    LmStudioJsonSchema,
)


def request() -> LmStudioChatRequest:
    return LmStudioChatRequest(
        model="local/story-model",
        messages=(LmStudioChatMessage("user", "Hallo"),),
        temperature=0.0,
        max_tokens=16,
        response_format=LmStudioJsonSchema(
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
    http_client = httpx.Client(transport=transport, base_url="http://lmstudio.test/v1/")
    client = LmStudioClient(
        LmStudioSettings("http://lmstudio.test/v1", api_token="secret"),
        http_client=http_client,
    )

    response = client.complete(request())

    assert response.text == "Antwort"
    assert observed["url"] == "http://lmstudio.test/v1/chat/completions"
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


@pytest.mark.parametrize(
    ("status_code", "kind"),
    [
        (401, LmStudioErrorKind.AUTHENTICATION),
        (404, LmStudioErrorKind.MODEL_UNAVAILABLE),
        (413, LmStudioErrorKind.CONTEXT_LIMIT),
        (429, LmStudioErrorKind.RATE_LIMITED),
        (500, LmStudioErrorKind.UNAVAILABLE),
    ],
)
def test_client_maps_relevant_http_statuses(status_code: int, kind: LmStudioErrorKind) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(status_code, text="provider detail"))
    http_client = httpx.Client(transport=transport, base_url="http://lmstudio.test/v1/")
    client = LmStudioClient(LmStudioSettings("http://lmstudio.test/v1"), http_client=http_client)

    with pytest.raises(LmStudioClientError) as failure:
        client.complete(request())

    assert failure.value.kind == kind
    http_client.close()


def test_client_rejects_invalid_wire_response() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"choices": []}))
    http_client = httpx.Client(transport=transport, base_url="http://lmstudio.test/v1/")
    client = LmStudioClient(LmStudioSettings("http://lmstudio.test/v1"), http_client=http_client)

    with pytest.raises(LmStudioClientError) as failure:
        client.complete(request())

    assert failure.value.kind == LmStudioErrorKind.INVALID_RESPONSE
    http_client.close()
