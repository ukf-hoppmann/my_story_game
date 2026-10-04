from __future__ import annotations

import base64
import json

import httpx
import pytest

from story_game.application import Failure, Success
from story_game.application.scene_image import (
    ImageGenErrorKind,
    ImageRefinement,
    ImageRenderRequest,
)
from story_game.infrastructure.configuration import ModalCredentials, ModalSettings
from story_game.infrastructure.image import ModalSceneImageRenderer

SETTINGS = ModalSettings(
    url="https://gpu.example",
    control_url="https://control.example",
    model="z-image-turbo",
    timeout_seconds=30,
    negative_prompt="blurry",
    refine_negative_prompt="ugly",
)
CREDENTIALS = ModalCredentials("wk-1", "ws-2")
PNG = b"\x89PNG-first"
REFINED = b"\x89PNG-refined"


def renderer(handler, *, credentials=CREDENTIALS, settings=SETTINGS) -> ModalSceneImageRenderer:
    return ModalSceneImageRenderer(
        lambda: settings,
        lambda: credentials,
        httpx.Client(transport=httpx.MockTransport(handler)),
    )


def request(refinement=None, model="z-image-turbo") -> ImageRenderRequest:
    return ImageRenderRequest("a tavern", 42, 1024, 768, model, refinement)


def test_a_plain_render_posts_the_prompt_and_returns_the_bytes() -> None:
    seen: list[httpx.Request] = []

    def handler(http_request: httpx.Request) -> httpx.Response:
        seen.append(http_request)
        return httpx.Response(200, content=PNG, headers={"content-type": "image/png"})

    result = renderer(handler).render(request())

    assert isinstance(result, Success)
    assert (result.data.data, result.data.content_type) == (PNG, "image/png")
    (http_request,) = seen
    assert str(http_request.url) == "https://gpu.example/generate"
    assert http_request.headers["authorization"] == "Bearer wk-1.ws-2"
    assert json.loads(http_request.content) == {
        "prompt": "a tavern",
        "seed": 42,
        "width": 1024,
        "height": 768,
        "model": "z-image-turbo",
        "negative_prompt": "blurry",
    }


def test_the_model_is_omitted_when_none_is_chosen() -> None:
    bodies = []

    def handler(http_request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(http_request.content))
        return httpx.Response(200, content=PNG, headers={"content-type": "image/png"})

    renderer(handler).render(request(model=None))

    assert "model" not in bodies[0]


def test_a_refinement_sends_the_first_image_to_the_refine_stage() -> None:
    bodies = []

    def handler(http_request: httpx.Request) -> httpx.Response:
        body = json.loads(http_request.content)
        bodies.append(body)
        content = PNG if len(bodies) == 1 else REFINED
        return httpx.Response(200, content=content, headers={"content-type": "image/png"})

    result = renderer(handler).render(
        request(ImageRefinement("tavern, fire", "juggernaut-xl-ragnarok", 0.35))
    )

    assert isinstance(result, Success)
    assert result.data.data == REFINED
    refine = bodies[1]
    assert refine["prompt"] == "tavern, fire"
    assert refine["seed"] == 42
    assert base64.b64decode(refine["image"]) == PNG
    assert refine["image_strength"] == 0.65
    assert refine["refine_model"] == "juggernaut-xl-ragnarok"
    assert refine["negative_prompt"] == "ugly"


@pytest.mark.parametrize(
    ("status", "kind"),
    [
        (401, ImageGenErrorKind.AUTHENTICATION),
        (403, ImageGenErrorKind.AUTHENTICATION),
        (422, ImageGenErrorKind.INVALID_REQUEST),
        (500, ImageGenErrorKind.UNAVAILABLE),
        (503, ImageGenErrorKind.UNAVAILABLE),
    ],
)
def test_http_errors_are_translated(status: int, kind: ImageGenErrorKind) -> None:
    result = renderer(lambda r: httpx.Response(status, text="boom")).render(request())

    assert isinstance(result, Failure)
    assert result.error.kind is kind
    assert "boom" not in result.error.message


def test_a_timeout_and_a_connection_error_are_translated() -> None:
    def timeout(http_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=http_request)

    def refused(http_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=http_request)

    assert renderer(timeout).render(request()).error.kind is ImageGenErrorKind.TIMEOUT
    assert renderer(refused).render(request()).error.kind is ImageGenErrorKind.UNAVAILABLE


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"", headers={"content-type": "image/png"}),
        httpx.Response(200, content=b"{}", headers={"content-type": "application/json"}),
    ],
)
def test_an_empty_or_non_image_response_is_invalid(response: httpx.Response) -> None:
    result = renderer(lambda r: response).render(request())

    assert result.error.kind is ImageGenErrorKind.INVALID_RESPONSE


def test_missing_credentials_fail_without_any_http_call() -> None:
    calls = []

    def handler(http_request: httpx.Request) -> httpx.Response:
        calls.append(http_request)
        return httpx.Response(200, content=PNG, headers={"content-type": "image/png"})

    result = renderer(handler, credentials=None).render(request())

    assert result.error.kind is ImageGenErrorKind.CONFIGURATION
    assert calls == []


def test_a_failed_refine_stage_fails_the_whole_render() -> None:
    answers = iter(
        [
            httpx.Response(200, content=PNG, headers={"content-type": "image/png"}),
            httpx.Response(500),
        ]
    )

    result = renderer(lambda r: next(answers)).render(
        request(ImageRefinement("tavern", "refine-x", 0.4))
    )

    assert isinstance(result, Failure)
    assert result.error.kind is ImageGenErrorKind.UNAVAILABLE


def test_models_are_listed_and_split_into_main_and_refine() -> None:
    listing = [
        {"name": "z-image-turbo", "steps": 8, "guidance": 0.0, "downloaded": True},
        {"name": "juggernaut-xl-ragnarok", "kind": "sdxl", "downloaded": True},
        {"name": "not-downloaded", "downloaded": False},
    ]
    seen = []

    def handler(http_request: httpx.Request) -> httpx.Response:
        seen.append(http_request)
        return httpx.Response(200, json=listing)

    result = renderer(handler).list_models()

    assert isinstance(result, Success)
    main, refine = result.data
    assert [model.name for model in main] == ["z-image-turbo"]
    assert [model.name for model in refine] == ["juggernaut-xl-ragnarok"]
    assert str(seen[0].url) == "https://control.example/models"
    assert seen[0].headers["authorization"] == "Bearer wk-1.ws-2"


def test_a_malformed_model_listing_is_invalid() -> None:
    result = renderer(lambda r: httpx.Response(200, json={"models": []})).list_models()

    assert result.error.kind is ImageGenErrorKind.INVALID_RESPONSE
