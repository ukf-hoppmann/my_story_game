"""The admin endpoints for versioned system prompts."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from story_game.api import create_app
from story_game.api.auth import KeycloakTokenVerifier, VerifiedCaller
from story_game.api.config import ApiSettings
from story_game.api.dependencies import require_admin
from story_game.application import RunInitiator
from story_game.application.prompt_management import (
    ListPromptEntries,
    ListPromptHistory,
    PromptManagementOperations,
    ResetPromptText,
    SeedPromptPackages,
    SeedPromptPackagesRequest,
    UpdatePromptText,
)
from story_game.domain import StableId
from story_game.infrastructure.llm import FilePromptPackageCatalog
from tests.api.test_api import MemoryGameStore, build_dependencies
from tests.api.test_authentication import (
    ISSUER,
    _FakeJwksClient,
    _token,
    _token_with_roles,
)
from tests.application.prompt_store_double import InMemoryPromptStore
from tests.application.test_prompt_management import PROMPT_ROOT

URL = "/api/v1/admin/prompts"
ADMIN = VerifiedCaller(
    RunInitiator("http://keycloak.test/realms/story-game", "admin-1"),
    frozenset({"admin"}),
    "testadmin",
)


def _operations() -> PromptManagementOperations:
    source = FilePromptPackageCatalog(PROMPT_ROOT)
    store = InMemoryPromptStore()
    clock = lambda: datetime.now(UTC)  # noqa: E731
    SeedPromptPackages(source, store, store, StableId.new, clock).apply(
        SeedPromptPackagesRequest()
    )
    return PromptManagementOperations(
        entries=ListPromptEntries(store),
        history=ListPromptHistory(store),
        update=UpdatePromptText(store, store, StableId.new, clock),
        reset=ResetPromptText(source, store, store, StableId.new, clock),
    )


def _app(operations: PromptManagementOperations | None):  # type: ignore[no-untyped-def]
    from dataclasses import replace

    dependencies = replace(build_dependencies(MemoryGameStore()), prompt_management=operations)
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


def _entry(body: dict[str, Any], kind: str, key: str) -> dict[str, Any]:
    return next(e for e in body["entries"] if (e["kind"], e["key"]) == (kind, key))


def test_listing_returns_every_active_entry_with_its_provenance(admin: TestClient) -> None:
    response = admin.get(URL)

    assert response.status_code == 200
    body = response.json()
    assert (body["package_id"], body["package_version"]) == ("story.base", "1")
    task = _entry(body, "task", "story_generation")
    assert task["source"] == "toml_seed"
    assert task["is_active"] is True
    assert task["is_modified"] is False
    assert task["text"]
    option = _entry(body, "option", "tone/balanced")
    assert option["is_default"] is True
    directive = next(e for e in body["entries"] if e["kind"] == "directive")
    assert directive["task_ids"]


def test_saving_a_text_creates_a_new_version_and_keeps_the_history(admin: TestClient) -> None:
    saved = admin.put(
        URL, json={"kind": "task", "key": "story_generation", "text": "Neuer Prompt"}
    )

    assert saved.status_code == 200
    assert saved.json()["source"] == "ui"
    assert saved.json()["created_by"] == "testadmin"
    assert _entry(admin.get(URL).json(), "task", "story_generation")["is_modified"] is True
    history = admin.get(URL + "/history", params={"kind": "task", "key": "story_generation"})
    assert history.status_code == 200
    assert [v["source"] for v in history.json()["versions"]] == ["ui", "toml_seed"]
    assert [v["is_active"] for v in history.json()["versions"]] == [True, False]


def test_an_empty_text_is_rejected(admin: TestClient) -> None:
    response = admin.put(URL, json={"kind": "task", "key": "story_generation", "text": "  "})

    assert response.status_code == 422


def test_saving_an_unknown_entry_is_not_found(admin: TestClient) -> None:
    response = admin.put(URL, json={"kind": "task", "key": "nope", "text": "Text"})

    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_the_history_of_an_unknown_entry_is_not_found(admin: TestClient) -> None:
    response = admin.get(URL + "/history", params={"kind": "task", "key": "nope"})

    assert response.status_code == 404


def test_resetting_one_entry_restores_the_original_text(admin: TestClient) -> None:
    original = _entry(admin.get(URL).json(), "task", "story_generation")["text"]
    admin.put(URL, json={"kind": "task", "key": "story_generation", "text": "Geändert"})

    reset = admin.post(URL + "/reset", json={"kind": "task", "key": "story_generation"})

    assert reset.status_code == 200
    assert [v["source"] for v in reset.json()["versions"]] == ["toml_reset"]
    current = _entry(admin.get(URL).json(), "task", "story_generation")
    assert current["text"] == original
    assert current["is_modified"] is False
    history = admin.get(URL + "/history", params={"kind": "task", "key": "story_generation"})
    assert [v["source"] for v in history.json()["versions"]] == ["toml_reset", "ui", "toml_seed"]


def test_resetting_everything_restores_all_changed_entries(admin: TestClient) -> None:
    admin.put(URL, json={"kind": "task", "key": "story_generation", "text": "A"})
    admin.put(URL, json={"kind": "option", "key": "tone/balanced", "text": "B"})

    reset = admin.post(URL + "/reset", json={})

    assert reset.status_code == 200
    assert {(v["kind"], v["key"]) for v in reset.json()["versions"]} == {
        ("task", "story_generation"),
        ("option", "tone/balanced"),
    }


def test_a_reset_naming_only_a_kind_is_rejected(admin: TestClient) -> None:
    assert admin.post(URL + "/reset", json={"kind": "task"}).status_code == 422


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", URL, None),
        ("GET", URL + "/history?kind=task&key=story_generation", None),
        ("PUT", URL, {"kind": "task", "key": "story_generation", "text": "x"}),
        ("POST", URL + "/reset", {}),
    ],
)
def test_the_endpoints_require_the_admin_role(
    secured: TestClient, method: str, path: str, body: dict[str, Any] | None
) -> None:
    anonymous = secured.request(method, path, json=body)
    player = secured.request(
        method,
        path,
        json=body,
        headers={"Authorization": f"Bearer {_token()}"},
    )
    other_role = secured.request(
        method,
        path,
        json=body,
        headers={"Authorization": f"Bearer {_token_with_roles(['offline_access'])}"},
    )
    admin_call = secured.request(
        method,
        path,
        json=body,
        headers={"Authorization": f"Bearer {_token_with_roles(['admin'])}"},
    )

    assert anonymous.status_code == 401
    assert player.status_code == 403
    assert other_role.status_code == 403
    assert admin_call.status_code == 200
