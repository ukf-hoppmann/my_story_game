from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from story_game.api import create_app
from story_game.api.dependencies import ApiDependencies
from story_game.application.game_state import (
    CommitCompletedTurn,
    CreateGameRun,
    GameStateOperations,
    LoadGame,
    UpdateGameConfiguration,
)
from story_game.application.game_models import (
    CompletedTurnPersistenceRequest,
    ConfigurationPersistenceRequest,
)
from story_game.application.ports import GameStateConflictError, GameStateNotFoundError
from story_game.domain import GameRun, GameState, StableId, StateRevision


class MemoryGameStore:
    def __init__(self) -> None:
        self.run: GameRun | None = None
        self.states: dict[StateRevision, GameState] = {}

    def create(self, run: GameRun, state: GameState) -> None:
        if self.run is not None:
            raise GameStateConflictError("exists")
        self.run = run
        self.states[state.revision] = state

    def load_run(self, run_id: StableId) -> GameRun:
        if self.run is None or self.run.id != run_id:
            raise GameStateNotFoundError("missing")
        return self.run

    def load_state(
        self, run_id: StableId, *, revision: StateRevision | None = None
    ) -> GameState:
        run = self.load_run(run_id)
        selected = revision or run.current_revision
        try:
            return self.states[selected]
        except KeyError as error:
            raise GameStateNotFoundError("missing revision") from error

    def update_configuration(
        self, request: ConfigurationPersistenceRequest
    ) -> GameState:
        raise AssertionError("The test API does not expose configuration updates")

    def commit_turn(self, request: CompletedTurnPersistenceRequest) -> GameState:
        raise AssertionError("The test API does not expose completed turns")


@pytest.fixture
def client() -> Iterator[TestClient]:
    store = MemoryGameStore()
    operations = GameStateOperations(
        create=CreateGameRun(store),
        load=LoadGame(store, store),
        update_configuration=UpdateGameConfiguration(store),
        commit_turn=CommitCompletedTurn(store, store),
    )
    with TestClient(create_app(ApiDependencies(operations))) as test_client:
        yield test_client


def complete_state_document() -> dict[str, object]:
    timestamp = "2026-08-06T00:00:00Z"
    return {
        "schema_version": 1,
        "game_run": {
            "id": "run-1",
            "status": "draft",
            "current_revision": 1,
            "members": [
                {
                    "issuer": "issuer",
                    "subject": "subject",
                    "game_role": "owner",
                    "player_entity_id": "almas",
                }
            ],
            "created_at": timestamp,
            "updated_at": timestamp,
        },
        "game_state": {
            "run_id": "run-1",
            "revision": 1,
            "configuration": {
                "language": "de",
                "narration_style_id": "style.dark",
                "perspective_id": "perspective.third-person",
                "control_mode_id": "control.player",
                "narrative_boundaries": ["Keine sexualisierte Gewalt"],
                "story_model_id": "model.story",
                "extraction_model_id": "model.extraction",
                "summary_model_id": "model.summary",
                "prompt_package_id": "story.base",
                "prompt_package_version": "1",
            },
            "world": {
                "entities": [
                    {
                        "id": "almas",
                        "kind": "character",
                        "label": "Almas",
                        "description": "",
                        "actor": {"role": "player"},
                        "conditions": [],
                        "aliases": [],
                    }
                ],
                "links": [],
                "facts": [],
                "knowledge": [],
                "rules": [],
                "goals": [
                    {
                        "id": "find-sword",
                        "kind": "main",
                        "title": "Finde das magische Schwert",
                        "description": "Almas muss das Schwert finden.",
                        "status": "open",
                        "related_entity_ids": ["almas"],
                    }
                ],
            },
            "story": {
                "turns": [],
                "summary": None,
                "current_turn_sequence": 0,
            },
        },
    }


def test_api_saves_and_loads_the_complete_state_document(client: TestClient) -> None:
    document = complete_state_document()

    created = client.post("/api/v1/runs", json=document)
    loaded = client.get("/api/v1/runs/run-1/state")

    assert created.status_code == 201
    assert created.json() == document
    assert loaded.status_code == 200
    assert loaded.json() == document


def test_api_rejects_inconsistent_run_and_state_ids(client: TestClient) -> None:
    document = complete_state_document()
    document["game_state"]["run_id"] = "another-run"  # type: ignore[index]

    response = client.post("/api/v1/runs", json=document)

    assert response.status_code == 422


def test_health_endpoint_is_independent_of_persistence(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
