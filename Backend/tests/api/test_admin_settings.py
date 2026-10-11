"""The admin endpoint for the global world-tracking switch."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from story_game.api import create_app
from story_game.api.auth import KeycloakTokenVerifier, VerifiedCaller
from story_game.api.config import ApiSettings
from story_game.api.dependencies import require_admin
from story_game.application import RunInitiator
from story_game.application.world_tracking import (
    GetWorldTracking,
    SetWorldTracking,
    WorldTrackingOperations,
    WorldTrackingSetting,
    WorldTrackingStoreError,
)
from tests.api.test_api import MemoryGameStore, build_dependencies
from tests.api.test_authentication import ISSUER, _FakeJwksClient, _token
from tests.application.world_tracking_double import InMemoryWorldTrackingStore

URL = "/api/v1/admin/settings/world-tracking"
NOW = datetime(2026, 10, 11, 12, tzinfo=UTC)
ADMIN = VerifiedCaller(
    RunInitiator("http://keycloak.test/realms/story-game", "admin-1"),
    frozenset({"admin"}),
    "testadmin",
)


def _app(store: InMemoryWorldTrackingStore):  # type: ignore[no-untyped-def]
    operations = WorldTrackingOperations(
        get=GetWorldTracking(store), set=SetWorldTracking(store, now=lambda: NOW)
    )
    dependencies = replace(build_dependencies(MemoryGameStore()), world_tracking=operations)
    return create_app(
        dependencies, settings=ApiSettings(keycloak_issuer=ISSUER, keycloak_audience=None)
    )


@pytest.fixture
def store() -> InMemoryWorldTrackingStore:
    return InMemoryWorldTrackingStore()


@pytest.fixture
def admin(store: InMemoryWorldTrackingStore) -> Iterator[TestClient]:
    app = _app(store)
    app.dependency_overrides[require_admin] = lambda: ADMIN
    with TestClient(app) as client:
        yield client


def test_world_tracking_is_enabled_until_an_admin_changes_it(admin: TestClient) -> None:
    response = admin.get(URL)

    assert response.status_code == 200
    assert response.json() == {"enabled": True, "updated_at": None, "updated_by": None}


def test_an_admin_can_switch_world_tracking_off(admin: TestClient) -> None:
    saved = admin.put(URL, json={"enabled": False})

    assert saved.status_code == 200
    assert saved.json()["enabled"] is False
    assert saved.json()["updated_by"] == "testadmin"
    assert admin.get(URL).json()["enabled"] is False


def test_a_store_failure_is_reported_as_unavailable(
    admin: TestClient, store: InMemoryWorldTrackingStore
) -> None:
    store.fail_with = WorldTrackingStoreError("kaputt")

    response = admin.get(URL)

    assert response.status_code == 503
    assert response.json()["error"] == "persistence_unavailable"


def test_a_player_without_the_admin_role_is_rejected(store: InMemoryWorldTrackingStore) -> None:
    with TestClient(_app(store)) as client:
        client.app.state.token_verifier = KeycloakTokenVerifier(ISSUER, None)
        client.app.state.token_verifier._jwks_client = _FakeJwksClient()  # type: ignore[attr-defined]
        headers = {"Authorization": f"Bearer {_token()}"}

        assert client.get(URL, headers=headers).status_code == 403
        assert client.put(URL, json={"enabled": False}, headers=headers).status_code == 403
    assert store.stored is None


PLAYER_URL = "/api/v1/settings/world-tracking"


def test_any_signed_in_player_can_read_whether_world_tracking_is_on(
    store: InMemoryWorldTrackingStore,
) -> None:
    with TestClient(_app(store)) as client:
        client.app.state.token_verifier = KeycloakTokenVerifier(ISSUER, None)
        client.app.state.token_verifier._jwks_client = _FakeJwksClient()  # type: ignore[attr-defined]
        headers = {"Authorization": f"Bearer {_token()}"}

        assert client.get(PLAYER_URL, headers=headers).json() == {"enabled": True}
        store.stored = WorldTrackingSetting(False, NOW, "testadmin")
        assert client.get(PLAYER_URL, headers=headers).json() == {"enabled": False}
        assert client.get(PLAYER_URL).status_code == 401
