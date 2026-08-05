from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from story_game.api.app import create_app  # noqa: E402
from story_game.application.game_state_service import GameStateService  # noqa: E402
from story_game.infrastructure.persistence.json.store import (  # noqa: E402
    JsonGameStateStore,
)


FIXTURES = Path(__file__).parents[1] / "fixtures"


def fixture_document(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def client(tmp_path: Path):
    store = JsonGameStateStore(tmp_path / "api-state.json")
    service = GameStateService(store, store)
    with TestClient(create_app(service)) as test_client:
        yield test_client


def test_api_creates_and_loads_a_state(client: TestClient) -> None:
    initial = fixture_document("game_state_initial.json")

    created = client.post("/api/v1/runs", json=initial)
    loaded = client.get("/api/v1/runs/run-ashfall/state")

    assert created.status_code == 201
    assert created.json() == initial
    assert loaded.status_code == 200
    assert loaded.json() == initial


def test_api_commits_only_typed_approved_changes(client: TestClient) -> None:
    initial = fixture_document("game_state_initial.json")
    expected = fixture_document("game_state_revision_2.json")
    assert isinstance(initial["world"], dict)
    assert isinstance(expected["world"], dict)
    assert isinstance(expected["story"], dict)

    assert client.post("/api/v1/runs", json=initial).status_code == 201
    world = expected["world"]
    story = expected["story"]
    assert isinstance(world, dict)
    assert isinstance(story, dict)
    changes = {
        "proposal_id": "proposal-api",
        "base_revision": 1,
        "changes": [
            {"type": "create_entity", "entity": world["entities"][-1]},
            {"type": "add_link", "link": world["links"][-1]},
            {"type": "add_fact", "fact": world["facts"][-1]},
            {"type": "grant_knowledge", "entry": world["knowledge"][-1]},
            {"type": "record_event", "event": story["events"][-1]},
        ],
    }

    committed = client.post(
        "/api/v1/runs/run-ashfall/commits",
        json=changes,
    )

    assert committed.status_code == 200
    assert committed.json() == expected


def test_api_returns_conflict_for_a_stale_revision(client: TestClient) -> None:
    initial = fixture_document("game_state_initial.json")
    assert client.post("/api/v1/runs", json=initial).status_code == 201
    first_commit = client.post(
        "/api/v1/runs/run-ashfall/commits",
        json={
            "proposal_id": "first-proposal",
            "base_revision": 1,
            "changes": [],
        },
    )
    stale_commit = client.post(
        "/api/v1/runs/run-ashfall/commits",
        json={
            "proposal_id": "stale-proposal",
            "base_revision": 1,
            "changes": [],
        },
    )

    assert first_commit.status_code == 200
    assert stale_commit.status_code == 409
    assert stale_commit.json()["error"] == "revision_conflict"


def test_health_endpoint_is_independent_of_persistence(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_rejects_unreviewed_operation_shapes_at_the_http_boundary(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/runs/run-ashfall/commits",
        json={
            "proposal_id": "unreviewed",
            "base_revision": 1,
            "changes": [{"type": "proposed_change_set", "content": "write it"}],
        },
    )

    assert response.status_code == 422
