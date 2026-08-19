from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from story_game.api import create_app
from story_game.api.config import ApiSettings
from story_game.api.dependencies import ApiDependencies
from story_game.api.mappers import game_from_api
from story_game.api.schemas.state import GameDocument
from story_game.application import (
    ConfirmGameRunProposal,
    ExtractInitialWorldState,
    ExtractStoryTurnChanges,
    GenerateStory,
    InitializeStory,
    PlayStoryTurn,
    ProposeGameRun,
    StartPlaythrough,
    SummarizeStory,
    Success,
)
from story_game.application.approve_story_turn_changes import ApproveStoryTurnChanges
from story_game.application.game_models import RunSummary
from story_game.application.game_state import (
    CommitCompletedTurn,
    CreateGameRun,
    GameStateOperations,
    ListPlayableRuns,
    LoadGame,
    PromptProfileValidator,
    UpdateGameConfiguration,
)
from story_game.application.llm import (
    CandidateEntity,
    ExtractionPromptSelectionResolver,
    InitialExtractionPromptSelectionResolver,
    StoryInitializationPromptResolver,
    StoryPromptSelectionResolver,
    SummaryPromptSelectionResolver,
    WorldInitializationCandidate,
)
from story_game.application.ports import GameStateConflictError, GameStateNotFoundError
from story_game.application.story_initialization import GenerateInitialStoryState
from story_game.application.story_turn_context import build_story_turn_context_selection
from story_game.domain import (
    EntityKind,
    GameRole,
    GameRun,
    GameRunMember,
    GameRunStatus,
    GameState,
    StableId,
    StateRevision,
)
from story_game.infrastructure.llm import FilePromptPackageCatalog
from story_game.infrastructure.persistence.in_memory_proposal_store import (
    InMemoryProposalStore,
)
from tests.ids import uuid_text

from tests.api.llm_doubles import (
    FakeGenerationConfigurationResolver,
    FakeInitialWorldExtractionPort,
    FakeStoryGenerationPort,
    FakeStoryInitializationPort,
    FakeStorySummaryPort,
    FakeTurnExtractionPort,
)

PROMPT_ROOT = Path(__file__).resolve().parents[2] / "prompts"
DEV_ISSUER = ApiSettings().dev_issuer
DEV_SUBJECT = ApiSettings().dev_subject


class MemoryGameStore:
    """Holds any number of runs/states in process memory, never on disk."""

    def __init__(self) -> None:
        self.runs: dict[StableId, GameRun] = {}
        self.states: dict[StableId, dict[StateRevision, GameState]] = {}

    def create(self, run: GameRun, state: GameState) -> None:
        if run.id in self.runs:
            raise GameStateConflictError("exists")
        self.runs[run.id] = run
        self.states[run.id] = {state.revision: state}

    def load_run(self, run_id: StableId) -> GameRun:
        try:
            return self.runs[run_id]
        except KeyError as error:
            raise GameStateNotFoundError("missing") from error

    def load_state(
        self, run_id: StableId, *, revision: StateRevision | None = None
    ) -> GameState:
        run = self.load_run(run_id)
        selected = revision or run.current_revision
        try:
            return self.states[run_id][selected]
        except KeyError as error:
            raise GameStateNotFoundError("missing revision") from error

    def update_configuration(self, request) -> GameState:
        raise AssertionError("The test API does not expose configuration updates")

    def commit_turn(self, request) -> GameState:
        run = self.runs[request.run_id]
        current = self.states[request.run_id][run.current_revision]
        updated = current.complete_turn(request.changes, request.turn, request.summary)
        self.states[request.run_id][updated.revision] = updated
        self.runs[request.run_id] = replace(
            run, current_revision=updated.revision, updated_at=request.turn.completed_at
        )
        return updated

    def list_for_member(self, issuer: str, subject: str) -> tuple[RunSummary, ...]:
        return tuple(
            RunSummary(
                run_id=run.id,
                name=run.name,
                status=run.status,
                current_revision=run.current_revision,
                game_role=member.game_role,
                updated_at=run.updated_at,
            )
            for run in self.runs.values()
            for member in run.members
            if member.issuer == issuer and member.subject == subject
        )


def build_dependencies(
    store: MemoryGameStore, *, extraction_port=None
) -> ApiDependencies:
    catalog = FilePromptPackageCatalog(PROMPT_ROOT)
    validator = PromptProfileValidator(catalog)
    generation_config = FakeGenerationConfigurationResolver()
    proposal_store = InMemoryProposalStore()

    operations = GameStateOperations(
        create=CreateGameRun(store, validator),
        load=LoadGame(store, store),
        update_configuration=UpdateGameConfiguration(store, validator),
        commit_turn=CommitCompletedTurn(store, store),
        list_playable_runs=ListPlayableRuns(store),
    )
    propose_run = ProposeGameRun(
        InitializeStory(
            GenerateInitialStoryState(
                StoryInitializationPromptResolver(catalog),
                generation_config,
                FakeStoryInitializationPort(),
                lambda: datetime.now(UTC),
            ),
            ExtractInitialWorldState(
                InitialExtractionPromptSelectionResolver(catalog),
                generation_config,
                extraction_port or FakeInitialWorldExtractionPort(),
            ),
        ),
        proposal_store,
    )
    confirm_proposal = ConfirmGameRunProposal(proposal_store, CreateGameRun(store, validator))
    play_turn = PlayStoryTurn(
        LoadGame(store, store),
        build_story_turn_context_selection(),
        GenerateStory(
            StoryPromptSelectionResolver(catalog),
            generation_config,
            FakeStoryGenerationPort(),
        ),
        ExtractStoryTurnChanges(
            ExtractionPromptSelectionResolver(catalog),
            generation_config,
            FakeTurnExtractionPort(),
        ),
        ApproveStoryTurnChanges(),
        SummarizeStory(
            SummaryPromptSelectionResolver(catalog),
            generation_config,
            FakeStorySummaryPort(),
        ),
        CommitCompletedTurn(store, store),
    )
    start_playthrough = StartPlaythrough(LoadGame(store, store), CreateGameRun(store, validator))
    return ApiDependencies(operations, propose_run, confirm_proposal, play_turn, start_playthrough)


@pytest.fixture
def store() -> MemoryGameStore:
    return MemoryGameStore()


@pytest.fixture
def client(store: MemoryGameStore) -> Iterator[TestClient]:
    with TestClient(create_app(build_dependencies(store), settings=ApiSettings())) as test_client:
        yield test_client


def start_draft_run(
    client: TestClient,
    *,
    run_name: str = "Der Leuchtturm von Talmoor",
    initial_prompt: str = "Ein Licht brennt, wo keines brennen sollte.",
    control_mode: str = "director",
    controllable_characters: list[dict] | None = None,
    character_decisions: list[dict] | None = None,
    item_decisions: list[dict] | None = None,
) -> dict:
    """Propose then immediately confirm — the two-step equivalent of what
    used to be one ``POST /api/v1/runs`` call, for tests that only care
    about the resulting DRAFT and are not exercising the proposal step
    itself."""
    proposal = client.post(
        "/api/v1/runs/proposals",
        json={
            "initial_prompt": initial_prompt,
            "control_mode": control_mode,
            "controllable_characters": controllable_characters or [],
        },
    ).json()
    confirmed = client.post(
        "/api/v1/runs",
        json={
            "proposal_id": proposal["proposal_id"],
            "run_name": run_name,
            "character_decisions": character_decisions or [],
            "item_decisions": item_decisions or [],
        },
    )
    return confirmed.json()


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
                    "controlled_entity_ids": [uuid_text("almas")],
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
                    },
                    {
                        "id": uuid_text("dungeon"),
                        "kind": "location",
                        "label": "Dungeonkammer",
                        "description": "",
                        "actor": None,
                        "conditions": [],
                        "aliases": [],
                    },
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
                "scene_location_ids": [uuid_text("dungeon")],
            },
            "story": {
                "turns": [],
                "summary": None,
                "current_turn_sequence": 0,
            },
        },
    }


def seed_document(store: MemoryGameStore, document: dict[str, object]) -> None:
    loaded = game_from_api(GameDocument.model_validate(document))
    store.create(loaded.run, loaded.state)


def test_api_loads_a_seeded_complete_state_document(
    client: TestClient, store: MemoryGameStore
) -> None:
    document = complete_state_document()
    seed_document(store, document)

    loaded = client.get(f"/api/v1/runs/{uuid_text('run-1')}")

    assert loaded.status_code == 200
    assert loaded.json() == document


def test_api_rejects_a_non_uuid_run_path(client: TestClient) -> None:
    response = client.get("/api/v1/runs/run-1")

    assert response.status_code == 422


def test_health_endpoint_is_independent_of_persistence(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_api_proposes_without_persisting_anything() -> None:
    store = MemoryGameStore()
    with TestClient(
        create_app(build_dependencies(store), settings=ApiSettings())
    ) as client:
        response = client.post(
            "/api/v1/runs/proposals",
            json={
                "initial_prompt": "Ein Licht brennt, wo keines brennen sollte.",
                "control_mode": "director",
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert "proposal_id" in body
        assert body["opening_narration"]
        assert body["suggested_title"]
        assert store.runs == {}


def test_api_starts_a_new_draft_run(client: TestClient) -> None:
    body = start_draft_run(client)

    assert body["game_run"]["status"] == "draft"
    assert body["game_state"]["revision"] == 1


def test_api_confirming_without_a_run_name_uses_the_suggested_title(
    store: MemoryGameStore,
) -> None:
    class TitledExtractionPort:
        def extract(self, call):
            return Success(
                WorldInitializationCandidate(suggested_title="Der Turm von Talmoor")
            )

    with TestClient(
        create_app(
            build_dependencies(store, extraction_port=TitledExtractionPort()),
            settings=ApiSettings(),
        )
    ) as client:
        proposal = client.post(
            "/api/v1/runs/proposals",
            json={
                "initial_prompt": "Ein Licht brennt, wo keines brennen sollte.",
                "control_mode": "director",
            },
        ).json()
        assert proposal["suggested_title"] == "Der Turm von Talmoor"

        confirmed = client.post(
            "/api/v1/runs",
            json={
                "proposal_id": proposal["proposal_id"],
                "character_decisions": [],
                "item_decisions": [],
            },
        )

        assert confirmed.status_code == 201
        assert confirmed.json()["game_run"]["name"] == "Der Turm von Talmoor"


def test_api_confirming_lets_the_caller_assign_and_reject_proposed_characters(
    store: MemoryGameStore,
) -> None:
    class TwoCharacterExtractionPort:
        def extract(self, call):
            return Success(
                WorldInitializationCandidate(
                    entities=(
                        CandidateEntity("maren", EntityKind.CHARACTER, "Maren"),
                        CandidateEntity("jonas", EntityKind.CHARACTER, "Jonas"),
                    )
                )
            )

    with TestClient(
        create_app(
            build_dependencies(store, extraction_port=TwoCharacterExtractionPort()),
            settings=ApiSettings(),
        )
    ) as client:
        proposal = client.post(
            "/api/v1/runs/proposals",
            json={
                "initial_prompt": "Maren und Jonas erreichen den Turm.",
                "control_mode": "director",
                "controllable_characters": [{"name": "Maren"}],
            },
        ).json()

        assert len(proposal["suggested_player_entity_ids"]) == 1
        maren_id, jonas_id = (
            entity["id"] for entity in proposal["world"]["entities"]
        )
        assert proposal["suggested_player_entity_ids"] == [maren_id]

        confirmed = client.post(
            "/api/v1/runs",
            json={
                "proposal_id": proposal["proposal_id"],
                "run_name": "Der Leuchtturm von Talmoor",
                "character_decisions": [
                    {"entity_id": maren_id, "role": "player", "removed": False},
                    {"entity_id": jonas_id, "role": "npc", "removed": True},
                ],
            },
        )

        assert confirmed.status_code == 201
        body = confirmed.json()
        member = body["game_run"]["members"][0]
        assert member["controlled_entity_ids"] == [maren_id]
        world_entity_ids = {
            entity["id"] for entity in body["game_state"]["world"]["entities"]
        }
        assert world_entity_ids == {maren_id}


def test_api_lists_runs_for_the_dev_identity(client: TestClient) -> None:
    created = start_draft_run(client)

    listed = client.get("/api/v1/runs")

    assert listed.status_code == 200
    run_ids = [entry["id"] for entry in listed.json()["runs"]]
    assert created["game_run"]["id"] in run_ids


def test_api_starts_a_playthrough_from_a_draft(client: TestClient) -> None:
    draft = start_draft_run(client)

    playthrough = client.post(
        f"/api/v1/runs/{draft['game_run']['id']}/playthroughs"
    )

    assert playthrough.status_code == 201
    body = playthrough.json()
    assert body["game_run"]["status"] == "active"
    assert body["game_run"]["id"] != draft["game_run"]["id"]
    assert body["game_state"]["world"] == draft["game_state"]["world"]


def test_api_rejects_a_playthrough_from_a_non_draft_source(client: TestClient) -> None:
    draft = start_draft_run(client)
    active = client.post(
        f"/api/v1/runs/{draft['game_run']['id']}/playthroughs"
    ).json()

    response = client.post(f"/api/v1/runs/{active['game_run']['id']}/playthroughs")

    assert response.status_code == 409
    assert response.json()["error"] == "playthrough_source_not_draft"


def test_api_plays_a_turn_in_an_active_run(client: TestClient) -> None:
    draft = start_draft_run(client)
    active = client.post(
        f"/api/v1/runs/{draft['game_run']['id']}/playthroughs"
    ).json()

    response = client.post(
        f"/api/v1/runs/{active['game_run']['id']}/turns",
        json={"player_input": "Ich öffne die Tür."},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["state"]["revision"] == 2
    assert body["summary_failed"] is False


def test_api_rejects_a_turn_against_a_draft_run(client: TestClient) -> None:
    draft = start_draft_run(client)

    response = client.post(
        f"/api/v1/runs/{draft['game_run']['id']}/turns",
        json={"player_input": "Ich öffne die Tür."},
    )

    assert response.status_code == 409
    assert response.json()["error"] == "run_not_active"


def test_api_rejects_a_turn_for_an_unknown_member(
    client: TestClient, store: MemoryGameStore
) -> None:
    run_id = StableId.new()
    timestamp = datetime.now(UTC)
    run = GameRun(
        id=run_id,
        name="Fremder Lauf",
        status=GameRunStatus.ACTIVE,
        current_revision=StateRevision(1),
        members=(
            GameRunMember(
                issuer="https://someone-else.example/realm",
                subject="someone-else",
                game_role=GameRole.OWNER,
            ),
        ),
        created_at=timestamp,
        updated_at=timestamp,
    )
    document = complete_state_document()
    document["game_state"]["run_id"] = str(run_id.value)  # type: ignore[index]
    state = game_from_api(GameDocument.model_validate(document)).state
    state = replace(state, run_id=run_id)
    store.create(run, state)

    response = client.post(
        f"/api/v1/runs/{run_id.value}/turns",
        json={"player_input": "Ich öffne die Tür."},
    )

    assert response.status_code == 403
    assert response.json()["error"] == "not_a_run_member"
