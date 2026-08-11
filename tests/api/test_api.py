from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from story_game.api import create_app
from story_game.api.dependencies import ApiDependencies
from story_game.application.game_state import (
    CommitCompletedTurn,
    CreateGameRun,
    GameStateOperations,
    LoadGame,
    PromptProfileValidator,
    UpdateGameConfiguration,
)
from story_game.application.game_models import (
    CompletedTurnPersistenceRequest,
    ConfigurationPersistenceRequest,
)
from story_game.application.ports import GameStateConflictError, GameStateNotFoundError
from story_game.domain import GameRun, GameState, StableId, StateRevision
from story_game.infrastructure.llm import FilePromptPackageCatalog
from tests.ids import uuid_text


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
    validator = PromptProfileValidator(
        FilePromptPackageCatalog(Path(__file__).resolve().parents[2] / "prompts")
    )
    operations = GameStateOperations(
        create=CreateGameRun(store, validator),
        load=LoadGame(store, store),
        update_configuration=UpdateGameConfiguration(store, validator),
        commit_turn=CommitCompletedTurn(store, store),
    )
    with TestClient(create_app(ApiDependencies(operations))) as test_client:
        yield test_client


def complete_state_document() -> dict[str, object]:
    timestamp = "2026-08-06T00:00:00Z"
    return {
        "schema_version": 1,
        "game_run": {
            "id": uuid_text("run-1"),
            "name": "Almas und das magische Schwert",
            "status": "draft",
            "current_revision": 1,
            "members": [
                {
                    "issuer": "issuer",
                    "subject": "subject",
                    "game_role": "owner",
                    "player_entity_id": uuid_text("almas"),
                }
            ],
            "created_at": timestamp,
            "updated_at": timestamp,
        },
        "game_state": {
            "run_id": uuid_text("run-1"),
            "revision": 1,
            "configuration": {
                "language": "de",
                "prompt_profile": {
                    "genre": "dark_fantasy",
                    "tone": "balanced",
                    "prose_style": "balanced",
                    "perspective": "third_person_limited",
                    "pacing": "balanced",
                    "control_mode": "player",
                    "player_agency": "strict",
                    "consequence": "balanced",
                    "challenge": "balanced",
                    "content_profile": "teen",
                },
                "narrative_boundaries": ["Keine sexualisierte Gewalt"],
                "prompt_package_id": "story.base",
                "prompt_package_version": "1",
            },
            "world": {
                "entities": [
                    {
                        "id": uuid_text("almas"),
                        "kind": "character",
                        "label": "Almas",
                        "description": "",
                        "actor": {"role": "player"},
                        "conditions": [],
                        "aliases": [],
                    }
                ],
                "links": [],
                "facts": [
                    {
                        "id": uuid_text("dungeon-open"),
                        "statement": "Der Dungeon ist geöffnet.",
                        "visibility": {"scope": "public", "actor_id": None},
                        "subject_id": None,
                    }
                ],
                "knowledge": [],
                "rules": [
                    {
                        "id": uuid_text("silver-hurts-spirits"),
                        "statement": "Silber verletzt Geister.",
                        "visibility": {"scope": "public", "actor_id": None},
                    }
                ],
                "goals": [
                    {
                        "id": uuid_text("find-sword"),
                        "kind": "main",
                        "title": "Finde das magische Schwert",
                        "description": "Almas muss das Schwert finden.",
                        "status": "open",
                        "related_entity_ids": [uuid_text("almas")],
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
    loaded = client.get(f"/api/v1/runs/{uuid_text('run-1')}/state")

    assert created.status_code == 201
    assert created.json() == document
    assert loaded.status_code == 200
    assert loaded.json() == document


def test_api_rejects_inconsistent_run_and_state_ids(client: TestClient) -> None:
    document = complete_state_document()
    document["game_state"]["run_id"] = uuid_text("another-run")  # type: ignore[index]

    response = client.post("/api/v1/runs", json=document)

    assert response.status_code == 422


def test_api_rejects_non_uuid_internal_ids(client: TestClient) -> None:
    document = complete_state_document()
    document["game_run"]["id"] = "run-1"  # type: ignore[index]

    response = client.post("/api/v1/runs", json=document)

    assert response.status_code == 422


def test_api_rejects_a_non_uuid_run_path(client: TestClient) -> None:
    response = client.get("/api/v1/runs/run-1/state")

    assert response.status_code == 422


def test_api_reports_the_prompt_field_that_requires_a_new_selection(
    client: TestClient,
) -> None:
    document = complete_state_document()
    document["game_state"]["configuration"]["prompt_profile"]["tone"] = "unknown"  # type: ignore[index]

    response = client.post("/api/v1/runs", json=document)

    assert response.status_code == 422
    assert response.json() == {
        "error": "invalid_prompt_selection",
        "detail": "Die Option 'unknown' ist für die Kategorie 'tone' nicht verfügbar",
        "category": "tone",
        "option_id": "unknown",
    }


def test_api_rejects_removed_configuration_fields(client: TestClient) -> None:
    document = complete_state_document()
    document["game_state"]["configuration"]["narration_style_id"] = "style.dark"  # type: ignore[index]

    response = client.post("/api/v1/runs", json=document)

    assert response.status_code == 422


def test_health_endpoint_is_independent_of_persistence(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
