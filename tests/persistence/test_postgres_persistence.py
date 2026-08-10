from __future__ import annotations

import os
import socket
from datetime import UTC, datetime
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

from story_game.application.game_models import (  # noqa: E402
    CompletedTurnPersistenceRequest,
    ConfigurationPersistenceRequest,
)
from story_game.domain import (  # noqa: E402
    ActorProfile,
    ActorRole,
    AddGoal,
    ApprovedChangeSet,
    EntityKind,
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


POSTGRES_DSN = os.environ.get("STORY_GAME_POSTGRES_DSN")
if POSTGRES_DSN is None and os.environ.get("HARNESS_RUN_DIRECTORY"):
    try:
        socket.getaddrinfo("postgres", 5432)
    except socket.gaierror:
        pass
    else:
        POSTGRES_DSN = (
            "postgresql://story_game:story_game_test@postgres:5432/story_game"
        )


def sid(value: str) -> StableId:
    return StableId(value)


def configuration(tone: str = "balanced") -> GameConfiguration:
    return GameConfiguration(
        language="de",
        prompt_profile=PromptProfile(
            genre="dark_fantasy",
            tone=tone,
            prose_style="balanced",
            perspective="third_person_limited",
            pacing="balanced",
            control_mode="player",
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
        WorldState(entities=(almas,)),
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


def _delete_run(connections: PostgresConnectionFactory, run_id: StableId) -> None:
    with connections.connect() as connection:
        with connection.transaction():
            connection.execute("DELETE FROM game_runs WHERE run_id = %s", (str(run_id),))
