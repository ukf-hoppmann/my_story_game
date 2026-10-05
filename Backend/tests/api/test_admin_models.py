"""The admin endpoints for the versioned per-task model settings."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from story_game.api import create_app
from story_game.api.auth import KeycloakTokenVerifier, VerifiedCaller
from story_game.api.config import ApiSettings
from story_game.api.dependencies import require_admin
from story_game.application import RunInitiator
from story_game.application.model_settings import (
    ListModelSettingHistory,
    ListModelSettings,
    ModelSettingsOperations,
    ResetModelSettings,
    SeedModelSettings,
    SeedModelSettingsRequest,
    UpdateModelSetting,
)
from story_game.domain import StableId
from tests.api.test_api import MemoryGameStore, build_dependencies
from tests.api.test_authentication import (
    ISSUER,
    _FakeJwksClient,
    _token,
    _token_with_roles,
)
from tests.application.model_settings_double import FakeModelSource, InMemoryModelSettingsStore

URL = "/api/v1/admin/models"
ADMIN = VerifiedCaller(
    RunInitiator("http://keycloak.test/realms/story-game", "admin-1"),
    frozenset({"admin"}),
    "testadmin",
)


def _operations() -> ModelSettingsOperations:
    source = FakeModelSource()
    store = InMemoryModelSettingsStore()
    clock = lambda: datetime.now(UTC)  # noqa: E731
    SeedModelSettings(source, store, store, StableId.new, clock).apply(SeedModelSettingsRequest())
    return ModelSettingsOperations(
        overview=ListModelSettings(store, source),
        history=ListModelSettingHistory(store),
        update=UpdateModelSetting(store, store, source, StableId.new, clock),
        reset=ResetModelSettings(source, store, store, StableId.new, clock),
    )


def _app(operations: ModelSettingsOperations | None):  # type: ignore[no-untyped-def]
    dependencies = replace(build_dependencies(MemoryGameStore()), model_settings=operations)
    return create_app(
        dependencies, settings=ApiSettings(keycloak_issuer=ISSUER, keycloak_audience=None)
    )


@pytest.fixture
def admin() -> Iterator[TestClient]:
    app = _app(_operations())
    app.dependency_overrides[require_admin] = lambda: ADMIN
    with TestClient(app) as client:
        yield client


@pytest.fixture
def secured() -> Iterator[TestClient]:
    with TestClient(_app(_operations())) as client:
        client.app.state.token_verifier = KeycloakTokenVerifier(ISSUER, None)
        client.app.state.token_verifier._jwks_client = _FakeJwksClient()  # type: ignore[attr-defined]
        yield client


def _setting(body: dict[str, Any], task: str) -> dict[str, Any]:
    return next(s for s in body["settings"] if s["task"] == task)


def test_listing_returns_the_active_settings_and_the_selectable_models(admin: TestClient) -> None:
    response = admin.get(URL)

    assert response.status_code == 200
    body = response.json()
    assert [s["task"] for s in body["settings"]] == [
        "story",
        "extraction",
        "summary",
        "scene_image",
    ]
    story = _setting(body, "story")
    assert story["model_ref"] == "model.story.default"
    assert story["temperature"] == 0.5
    assert story["max_output_tokens"] is None
    assert story["source"] == "toml_seed"
    assert story["is_modified"] is False
    assert {c["model_ref"] for c in body["candidates"] if c["task"] == "story"} == {
        "model.story.default",
        "model.story.groq",
    }
    groq = next(c for c in body["candidates"] if c["model_ref"] == "model.story.groq")
    assert (groq["provider_id"], groq["model_id"]) == ("groq", "groq-story")


def test_saving_creates_a_new_version_and_keeps_the_history(admin: TestClient) -> None:
    saved = admin.put(
        URL,
        json={
            "task": "story",
            "model_ref": "model.story.groq",
            "temperature": 0.9,
            "max_output_tokens": 800,
        },
    )

    assert saved.status_code == 200
    assert saved.json()["created_by"] == "testadmin"
    assert saved.json()["is_modified"] is True
    assert _setting(admin.get(URL).json(), "story")["model_ref"] == "model.story.groq"
    history = admin.get(URL + "/history", params={"task": "story"})
    assert [v["source"] for v in history.json()["versions"]] == ["ui", "toml_seed"]


def test_options_may_be_left_empty(admin: TestClient) -> None:
    saved = admin.put(URL, json={"task": "story", "model_ref": "model.story.groq"})

    assert saved.status_code == 200
    assert saved.json()["temperature"] is None
    assert saved.json()["max_output_tokens"] is None


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"task": "story", "model_ref": "model.summary.default"}, "invalid_model_selection"),
        ({"task": "story", "model_ref": "model.story.default", "temperature": 5}, "invalid_generation_options"),
        ({"task": "story", "model_ref": "model.story.default", "max_output_tokens": 0}, "invalid_generation_options"),
    ],
)
def test_invalid_input_is_rejected(admin: TestClient, payload: dict[str, Any], code: str) -> None:
    response = admin.put(URL, json=payload)

    assert response.status_code == 422
    assert response.json()["error"] == code


def test_an_unknown_task_is_rejected(admin: TestClient) -> None:
    assert admin.put(URL, json={"task": "nope", "model_ref": "x"}).status_code == 422
    assert admin.get(URL + "/history", params={"task": "nope"}).status_code == 422


def test_resetting_one_task_restores_the_original(admin: TestClient) -> None:
    admin.put(URL, json={"task": "story", "model_ref": "model.story.groq", "temperature": 1})

    reset = admin.post(URL + "/reset", json={"task": "story"})

    assert reset.status_code == 200
    assert [v["source"] for v in reset.json()["versions"]] == ["toml_reset"]
    current = _setting(admin.get(URL).json(), "story")
    assert (current["model_ref"], current["temperature"]) == ("model.story.default", 0.5)
    assert current["is_modified"] is False


def test_resetting_everything_restores_all_changed_tasks(admin: TestClient) -> None:
    admin.put(URL, json={"task": "story", "model_ref": "model.story.groq"})
    admin.put(URL, json={"task": "summary", "model_ref": "model.summary.groq"})

    reset = admin.post(URL + "/reset", json={})

    assert {v["task"] for v in reset.json()["versions"]} == {"story", "summary"}


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", URL, None),
        ("GET", URL + "/history?task=story", None),
        ("PUT", URL, {"task": "story", "model_ref": "model.story.groq"}),
        ("POST", URL + "/reset", {}),
    ],
)
def test_the_endpoints_require_the_admin_role(
    secured: TestClient, method: str, path: str, body: dict[str, Any] | None
) -> None:
    def call(token: str | None) -> int:
        headers = {} if token is None else {"Authorization": f"Bearer {token}"}
        return secured.request(method, path, json=body, headers=headers).status_code

    assert call(None) == 401
    assert call(_token()) == 403
    assert call(_token_with_roles(["offline_access"])) == 403
    assert call(_token_with_roles(["admin"])) == 200
