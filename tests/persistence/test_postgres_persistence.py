from __future__ import annotations

import os
import socket
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

from story_game.application.game_models import (  # noqa: E402
    CompletedTurnPersistenceRequest,
    ConfigurationPersistenceRequest,
    LoadedGame,
)
from story_game.application import (  # noqa: E402
    Failure,
    InitializeGameRun,
    InitializeGameRunRequest,
    RunInitiator,
    Success,
)
from story_game.application.game_state import (  # noqa: E402
    CreateGameRun,
    PromptProfileValidator,
    RunConflict,
)
from story_game.application.initialization_models import (  # noqa: E402
    InitializedStory,
    PlayerCharacterSeed,
)
from story_game.domain import (  # noqa: E402
    ActorProfile,
    ActorRole,
    AddGoal,
    ApprovedChangeSet,
    EntityKind,
    Fact,
    GameConfiguration,
    GameRole,
    GameRun,
    GameRunMember,
    GameRunStatus,
    GameState,
    Goal,
    GoalKind,
    GoalStatus,
    PromptProfile,
    StableId,
    StateRevision,
    StorySequence,
    StoryState,
    StorySummary,
    StoryTurn,
    WorldEntity,
    WorldRule,
    WorldState,
)
from story_game.infrastructure.persistence.errors import (  # noqa: E402
    PersistenceConflictError,
    PersistenceNotFoundError,
)
from story_game.infrastructure.persistence.postgres import (  # noqa: E402
    PostgresConnectionFactory,
    PostgresGameStore,
    PostgresSchemaMigrator,
)
from story_game.infrastructure.llm import FilePromptPackageCatalog  # noqa: E402
from tests.ids import sid  # noqa: E402


POSTGRES_DSN = os.environ.get("STORY_GAME_POSTGRES_DSN")
PROMPT_ROOT = Path(__file__).resolve().parents[2] / "prompts"
if POSTGRES_DSN is None and os.environ.get("HARNESS_RUN_DIRECTORY"):
    try:
        socket.getaddrinfo("postgres", 5432)
    except socket.gaierror:
        pass
    else:
        POSTGRES_DSN = (
            "postgresql://story_game:story_game_test@postgres:5432/story_game"
        )


def configuration(
    tone: str = "balanced", *, control_mode: str = "player"
) -> GameConfiguration:
    return GameConfiguration(
        language="de",
        prompt_profile=PromptProfile(
            genre="dark_fantasy",
            tone=tone,
            prose_style="balanced",
            perspective="third_person_limited",
            pacing="balanced",
            control_mode=control_mode,
            player_agency="strict",
            consequence="balanced",
            challenge="balanced",
            content_profile="teen",
        ),
        narrative_boundaries=("Keine sexualisierte Gewalt",),
        prompt_package_id="story.base",
        prompt_package_version="1",
    )


def initial(run_id: StableId) -> tuple[GameRun, GameState]:
    timestamp = datetime(2026, 8, 6, tzinfo=UTC)
    almas = WorldEntity(
        sid("almas"),
        EntityKind.CHARACTER,
        "Almas",
        actor=ActorProfile(ActorRole.PLAYER),
    )
    run = GameRun(
        run_id,
        "Almas und das magische Schwert",
        GameRunStatus.DRAFT,
        StateRevision(1),
        (
            GameRunMember(
                "https://identity.example/realms/story",
                "user-1",
                GameRole.OWNER,
                almas.id,
            ),
        ),
        timestamp,
        timestamp,
    )
    state = GameState(
        run_id,
        StateRevision(1),
        configuration(),
        WorldState(
            entities=(almas,),
            facts=(Fact(sid("dungeon-open"), "Der Dungeon ist geöffnet."),),
            rules=(WorldRule(sid("silver"), "Silber verletzt Geister."),),
        ),
        StoryState(),
    )
    return run, state


@pytest.fixture
def postgres_store() -> tuple[PostgresGameStore, PostgresConnectionFactory]:
    if not POSTGRES_DSN:
        pytest.skip("STORY_GAME_POSTGRES_DSN ist für den PostgreSQL-Test nicht gesetzt")
    connections = PostgresConnectionFactory(POSTGRES_DSN)
    PostgresSchemaMigrator(connections).migrate()
    return PostgresGameStore(connections), connections


def test_postgres_roundtrips_a_complete_initial_game(
    postgres_store: tuple[PostgresGameStore, PostgresConnectionFactory],
) -> None:
    store, connections = postgres_store
    run_id = sid(f"integration-{uuid4()}")
    run, state = initial(run_id)

    try:
        store.create(run, state)

        assert store.load_run(run_id) == run
        assert store.load_state(run_id) == state
        assert store.load_state(run_id, revision=StateRevision(1)) == state
    finally:
        _delete_run(connections, run_id)


def test_initialize_game_run_persists_revision_one_atomically(
    postgres_store: tuple[PostgresGameStore, PostgresConnectionFactory],
) -> None:
    store, connections = postgres_store
    run_id = sid(f"initial-{uuid4()}")
    timestamp = datetime(2026, 8, 11, 9, tzinfo=UTC)
    player = WorldEntity(
        sid("initial-player"),
        EntityKind.CHARACTER,
        "Almas",
        actor=ActorProfile(ActorRole.PLAYER),
    )
    initialized = InitializedStory(
        StoryState(),
        WorldState(entities=(player,)),
    )

    class FixedInitializer:
        def apply(self, request: object) -> object:
            return Success(initialized)

    operation = InitializeGameRun(
        FixedInitializer(),  # type: ignore[arg-type]
        CreateGameRun(
            store,
            PromptProfileValidator(FilePromptPackageCatalog(PROMPT_ROOT)),
        ),
        new_id=lambda: run_id,
        now=lambda: timestamp,
    )

    try:
        result = operation.apply(
            InitializeGameRunRequest(
                configuration=configuration(),
                run_name="Almas und das magische Schwert",
                initial_prompt="Almas betritt den Dungeon.",
                initiator=RunInitiator("https://identity.example/story", "user-1"),
                player_character=PlayerCharacterSeed("Almas"),
            )
        )

        assert isinstance(result, Success)
        assert isinstance(result.data, LoadedGame)
        assert result.data.run.status is GameRunStatus.DRAFT
        assert result.data.run.current_revision == StateRevision(1)
        assert result.data.state.revision == StateRevision(1)
        assert store.load_run(run_id) == result.data.run
        assert store.load_state(run_id) == result.data.state
    finally:
        _delete_run(connections, run_id)


def test_initialize_game_run_maps_duplicate_uuid_to_conflict_without_overwrite(
    postgres_store: tuple[PostgresGameStore, PostgresConnectionFactory],
) -> None:
    store, connections = postgres_store
    run_id = sid(f"duplicate-{uuid4()}")
    timestamp = datetime(2026, 8, 11, 9, tzinfo=UTC)
    initialized = InitializedStory(StoryState(), WorldState())

    class FixedInitializer:
        def apply(self, request: object) -> object:
            return Success(initialized)

    creator = CreateGameRun(
        store,
        PromptProfileValidator(FilePromptPackageCatalog(PROMPT_ROOT)),
    )

    def operation() -> InitializeGameRun:
        return InitializeGameRun(
            FixedInitializer(),  # type: ignore[arg-type]
            creator,
            new_id=lambda: run_id,
            now=lambda: timestamp,
        )

    request = InitializeGameRunRequest(
        configuration=configuration(control_mode="director"),
        run_name="Leerer Regie-Start",
        initial_prompt="Die Szene beginnt.",
        initiator=RunInitiator("https://identity.example/story", "user-1"),
    )

    try:
        first = operation().apply(request)
        second = operation().apply(request)

        assert isinstance(first, Success)
        assert second == Failure(
            RunConflict(
                f"Der GameRun existiert bereits oder enthält doppelte Daten: {run_id}"
            )
        )
        assert store.load_run(run_id) == first.data.run
        assert store.load_state(run_id) == first.data.state
    finally:
        _delete_run(connections, run_id)


def test_configuration_revision_does_not_create_a_story_turn(
    postgres_store: tuple[PostgresGameStore, PostgresConnectionFactory],
) -> None:
    store, connections = postgres_store
    run_id = sid(f"integration-{uuid4()}")
    run, state = initial(run_id)

    try:
        store.create(run, state)
        updated = store.update_configuration(
            ConfigurationPersistenceRequest(
                run_id, StateRevision(1), configuration("dark")
            )
        )

        assert updated.revision == StateRevision(2)
        assert updated.configuration.prompt_profile.tone == "dark"
        assert updated.story == StoryState()
        assert store.load_state(run_id, revision=StateRevision(1)) == state
        assert store.load_run(run_id).current_revision == StateRevision(2)
    finally:
        _delete_run(connections, run_id)


def test_completed_turn_and_resulting_state_are_committed_atomically(
    postgres_store: tuple[PostgresGameStore, PostgresConnectionFactory],
) -> None:
    store, connections = postgres_store
    run_id = sid(f"integration-{uuid4()}")
    run, state = initial(run_id)
    goal = Goal(
        sid("find-sword"),
        GoalKind.MAIN,
        "Finde das magische Schwert",
        "Almas muss das Schwert im Dungeon finden.",
        GoalStatus.OPEN,
        (sid("almas"),),
    )
    turn = StoryTurn(
        sid("turn-1"),
        StorySequence(1),
        "Ich gehe in den Dungeon.",
        "Almas betritt den dunklen Dungeon.",
        StateRevision(1),
        StateRevision(2),
        datetime(2026, 8, 6, 10, tzinfo=UTC),
    )
    summary = StorySummary(
        StorySequence(1), "Almas hat den Dungeon betreten.", StateRevision(2)
    )

    try:
        store.create(run, state)
        updated = store.commit_turn(
            CompletedTurnPersistenceRequest(
                run_id,
                ApprovedChangeSet(
                    sid("proposal-1"), StateRevision(1), (AddGoal(goal),)
                ),
                turn,
                summary,
            )
        )

        assert updated.world.goal(goal.id) == goal
        assert updated.story.turns == (turn,)
        assert store.load_state(run_id, revision=StateRevision(1)) == state
        assert store.load_state(run_id, revision=StateRevision(2)) == updated
    finally:
        _delete_run(connections, run_id)


def test_stale_turn_leaves_no_partial_revision_or_turn(
    postgres_store: tuple[PostgresGameStore, PostgresConnectionFactory],
) -> None:
    store, connections = postgres_store
    run_id = sid(f"integration-{uuid4()}")
    run, state = initial(run_id)
    turn = StoryTurn(
        sid("turn-1"),
        StorySequence(1),
        "Weiter.",
        "Die Geschichte geht weiter.",
        StateRevision(1),
        StateRevision(2),
        datetime(2026, 8, 6, 10, tzinfo=UTC),
    )

    try:
        store.create(run, state)
        store.update_configuration(
            ConfigurationPersistenceRequest(run_id, StateRevision(1), configuration())
        )

        with pytest.raises(PersistenceConflictError):
            store.commit_turn(
                CompletedTurnPersistenceRequest(
                    run_id,
                    ApprovedChangeSet(sid("stale"), StateRevision(1)),
                    turn,
                    None,
                )
            )

        assert store.load_run(run_id).current_revision == StateRevision(2)
        with pytest.raises(PersistenceNotFoundError):
            store.load_state(run_id, revision=StateRevision(3))
    finally:
        _delete_run(connections, run_id)


def test_new_baseline_does_not_create_obsolete_story_tables(
    postgres_store: tuple[PostgresGameStore, PostgresConnectionFactory],
) -> None:
    _, connections = postgres_store
    obsolete = (
        "story_events",
        "story_scenes",
        "story_scene_participants",
        "story_chapters",
        "story_threads",
        "story_goals",
        "story_summaries",
    )
    with connections.connect() as connection:
        for table in obsolete:
            assert connection.execute(
                "SELECT to_regclass(%s) AS table_name", (table,)
            ).fetchone()["table_name"] is None


def test_new_baseline_has_no_persisted_evidence_columns(
    postgres_store: tuple[PostgresGameStore, PostgresConnectionFactory],
) -> None:
    _, connections = postgres_store
    with connections.connect() as connection:
        rows = connection.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name IN ('world_facts', 'world_rules')
              AND column_name LIKE 'evidence_%'
            """
        ).fetchall()

    assert rows == []


def test_new_baseline_uses_native_uuid_for_internal_id_columns(
    postgres_store: tuple[PostgresGameStore, PostgresConnectionFactory],
) -> None:
    _, connections = postgres_store
    expected_uuid_columns = {
        ("game_runs", "run_id"),
        ("game_run_members", "run_id"),
        ("game_run_members", "player_entity_id"),
        ("game_state_revisions", "run_id"),
        ("game_state_configurations", "run_id"),
        ("world_entities", "run_id"),
        ("world_entities", "entity_id"),
        ("world_links", "run_id"),
        ("world_links", "link_id"),
        ("world_links", "source_id"),
        ("world_links", "target_id"),
        ("world_links", "visibility_actor_id"),
        ("world_facts", "run_id"),
        ("world_facts", "fact_id"),
        ("world_facts", "subject_id"),
        ("world_facts", "visibility_actor_id"),
        ("world_knowledge", "run_id"),
        ("world_knowledge", "actor_id"),
        ("world_knowledge", "fact_id"),
        ("world_rules", "run_id"),
        ("world_rules", "rule_id"),
        ("world_rules", "visibility_actor_id"),
        ("world_goals", "run_id"),
        ("world_goals", "goal_id"),
        ("world_goal_related_entities", "run_id"),
        ("world_goal_related_entities", "goal_id"),
        ("world_goal_related_entities", "entity_id"),
        ("story_state_metadata", "run_id"),
        ("story_turns", "run_id"),
        ("story_turns", "turn_id"),
    }

    with connections.connect() as connection:
        rows = connection.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND data_type = 'uuid'
            """
        ).fetchall()

    assert {(row["table_name"], row["column_name"]) for row in rows} == (
        expected_uuid_columns
    )


def test_goal_entity_references_are_relational_not_json(
    postgres_store: tuple[PostgresGameStore, PostgresConnectionFactory],
) -> None:
    _, connections = postgres_store
    with connections.connect() as connection:
        obsolete_column = connection.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'world_goals'
              AND column_name = 'related_entity_ids'
            """
        ).fetchall()
        relation_table = connection.execute(
            "SELECT to_regclass('world_goal_related_entities') AS table_name"
        ).fetchone()

    assert obsolete_column == []
    assert relation_table["table_name"] == "world_goal_related_entities"


def _delete_run(connections: PostgresConnectionFactory, run_id: StableId) -> None:
    with connections.connect() as connection:
        with connection.transaction():
            connection.execute(
                "DELETE FROM game_runs WHERE run_id = %s", (run_id.value,)
            )
