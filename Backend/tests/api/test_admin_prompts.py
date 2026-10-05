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
    CreatePromptOption,
    ListCustomPromptOptions,
    ListPromptEntries,
    ListPromptHistory,
    PromptManagementOperations,
    RemovePromptOption,
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
from tests.application.prompt_store_double import FakeOptionUsage, InMemoryPromptStore
from tests.application.test_prompt_management import PROMPT_ROOT

URL = "/api/v1/admin/prompts"
ADMIN = VerifiedCaller(
    RunInitiator("http://keycloak.test/realms/story-game", "admin-1"),
    frozenset({"admin"}),
    "testadmin",
)


_USAGE = FakeOptionUsage()


def _operations() -> PromptManagementOperations:
    _USAGE.used.clear()
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
        create_option=CreatePromptOption(store, store, StableId.new, clock),
        custom_options=ListCustomPromptOptions(source, store),
        remove_option=RemovePromptOption(source, store, store, _USAGE),
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


def test_resetting_one_kind_leaves_the_other_kinds_untouched(admin: TestClient) -> None:
    admin.put(URL, json={"kind": "task", "key": "story_generation", "text": "A"})
    admin.put(URL, json={"kind": "option", "key": "tone/balanced", "text": "B"})

    reset = admin.post(URL + "/reset", json={"kind": "option"})

    assert reset.status_code == 200
    assert {(v["kind"], v["key"]) for v in reset.json()["versions"]} == {("option", "tone/balanced")}
    assert _entry(admin.get(URL).json(), "task", "story_generation")["is_modified"] is True


def test_a_reset_naming_only_a_key_is_rejected(admin: TestClient) -> None:
    assert admin.post(URL + "/reset", json={"key": "story_generation"}).status_code == 422


def _add(admin: TestClient, **overrides: str):  # type: ignore[no-untyped-def]
    body = {"category": "tone", "option_id": "melancholic", "text": "Wehmütig."} | overrides
    return admin.post(URL + "/options", json=body)


def test_a_new_option_shows_up_in_the_list_marked_as_custom(admin: TestClient) -> None:
    created = _add(admin)

    assert created.status_code == 201
    assert created.json()["key"] == "tone/melancholic"
    assert created.json()["created_by"] == "testadmin"
    assert created.json()["is_custom"] is True
    listed = _entry(admin.get(URL).json(), "option", "tone/melancholic")
    assert listed["is_custom"] is True
    assert listed["text"] == "Wehmütig."
    assert _entry(admin.get(URL).json(), "option", "tone/balanced")["is_custom"] is False


def test_an_edited_custom_option_stays_custom(admin: TestClient) -> None:
    _add(admin)

    saved = admin.put(URL, json={"kind": "option", "key": "tone/melancholic", "text": "Neu"})

    assert saved.json()["is_custom"] is True


@pytest.mark.parametrize(
    ("overrides", "status", "error"),
    [
        ({"category": "pacing"}, 422, "invalid_prompt_option"),
        ({"option_id": "Not A Slug"}, 422, "invalid_prompt_option"),
        ({"option_id": "dark"}, 409, "prompt_option_exists"),
        ({"text": "  "}, 422, None),
    ],
)
def test_a_new_option_is_validated(
    admin: TestClient, overrides: dict[str, str], status: int, error: str | None
) -> None:
    response = _add(admin, **overrides)

    assert response.status_code == status
    if error is not None:
        assert response.json()["error"] == error


def test_an_added_option_can_be_removed_again(admin: TestClient) -> None:
    _add(admin)

    removed = admin.delete(URL + "/options", params={"category": "tone", "option_id": "melancholic"})

    assert removed.status_code == 204
    keys = {e["key"] for e in admin.get(URL).json()["entries"]}
    assert "tone/melancholic" not in keys


def test_removing_a_shipped_option_is_refused(admin: TestClient) -> None:
    removed = admin.delete(URL + "/options", params={"category": "tone", "option_id": "dark"})

    assert removed.status_code == 409
    assert removed.json()["error"] == "prompt_option_not_removable"


def test_removing_an_option_in_use_is_refused(admin: TestClient) -> None:
    _add(admin)
    _USAGE.used.add(("tone", "melancholic"))

    removed = admin.delete(URL + "/options", params={"category": "tone", "option_id": "melancholic"})

    assert removed.status_code == 409
    assert removed.json()["error"] == "prompt_option_in_use"


def test_removing_an_unknown_option_is_not_found(admin: TestClient) -> None:
    removed = admin.delete(URL + "/options", params={"category": "tone", "option_id": "ghost"})

    assert removed.status_code == 404


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", URL, None),
        ("GET", URL + "/history?kind=task&key=story_generation", None),
        ("PUT", URL, {"kind": "task", "key": "story_generation", "text": "x"}),
        ("POST", URL + "/reset", {}),
        ("POST", URL + "/options", {"category": "tone", "option_id": "ab", "text": "x"}),
        ("DELETE", URL + "/options?category=tone&option_id=ab", None),
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
    assert admin_call.status_code not in (401, 403)  # past the role gate; the outcome varies
