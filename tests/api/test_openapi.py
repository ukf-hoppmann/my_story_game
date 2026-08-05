from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from story_game.api.app import create_app  # noqa: E402
from story_game.application.game_state import (  # noqa: E402
    CommitGameStateChanges,
    CreateInitialGameState,
    GameStateOperations,
    LoadGameState,
)
from story_game.infrastructure.persistence.json import (  # noqa: E402
    JsonGameStateDocumentCodec,
)
from story_game.infrastructure.persistence.json.store import (  # noqa: E402
    JsonGameStateStore,
)


def test_swagger_and_openapi_describe_the_state_routes(tmp_path: Path) -> None:
    store = JsonGameStateStore(tmp_path / "openapi-state.json")
    operations = GameStateOperations(
        CreateInitialGameState(store),
        LoadGameState(store),
        CommitGameStateChanges(store),
    )
    with TestClient(
        create_app(operations, JsonGameStateDocumentCodec())
    ) as client:
        swagger = client.get("/docs")
        schema = client.get("/openapi.json")

    assert swagger.status_code == 200
    assert "swagger-ui" in swagger.text
    assert schema.status_code == 200
    paths = schema.json()["paths"]
    assert "/api/v1/runs" in paths
    assert "/api/v1/runs/{run_id}/state" in paths
    assert "/api/v1/runs/{run_id}/commits" in paths
    assert "ApprovedChangeSetRequest" in schema.json()["components"]["schemas"]
