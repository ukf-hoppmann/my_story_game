from __future__ import annotations

import os
import socket
from pathlib import Path
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

from story_game.domain import (  # noqa: E402
    AddFact,
    AddLink,
    ApprovedChangeSet,
    CreateEntity,
    GrantKnowledge,
    RecordEvent,
    StableId,
    StateRevision,
)
from story_game.infrastructure.persistence.postgres import (  # noqa: E402
    PostgresConnectionFactory,
    PostgresGameStateStore,
    PostgresSchemaMigrator,
)
from story_game.infrastructure.persistence.errors import (  # noqa: E402
    PersistenceConflictError,
)
from story_game.infrastructure.persistence.json.mapper import (  # noqa: E402
    state_from_document,
)


FIXTURES = Path(__file__).parents[1] / "fixtures"
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


@pytest.fixture
def postgres_store() -> tuple[PostgresGameStateStore, PostgresConnectionFactory]:
    if not POSTGRES_DSN:
        pytest.skip("STORY_GAME_POSTGRES_DSN ist für den PostgreSQL-Test nicht gesetzt")
    connections = PostgresConnectionFactory(POSTGRES_DSN)
    PostgresSchemaMigrator(connections).migrate()
    return PostgresGameStateStore(connections), connections


def load_fixture(name: str):
    import json

    return state_from_document(
        json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    )


def test_postgres_persists_initial_state_history_and_approved_commit(
    postgres_store: tuple[PostgresGameStateStore, PostgresConnectionFactory],
) -> None:
    store, connections = postgres_store
    initial = load_fixture("game_state_initial.json")
    expected = load_fixture("game_state_revision_2.json")
    run_id = StableId(f"integration-{uuid4()}")
    initial = initial.__class__(
        id=run_id,
        revision=initial.revision,
        world=initial.world,
        story=initial.story,
        player_actor_id=initial.player_actor_id,
    )
    expected = expected.__class__(
        id=run_id,
        revision=expected.revision,
        world=expected.world,
        story=expected.story,
        player_actor_id=expected.player_actor_id,
    )

    try:
        store.create_initial(initial)
        assert store.load(run_id) == initial

        changes = ApprovedChangeSet(
            proposal_id=StableId(f"proposal-{uuid4()}"),
            base_revision=StateRevision(1),
            changes=(
                CreateEntity(expected.world.entity(StableId("lantern"))),
                AddLink(
                    next(
                        link
                        for link in expected.world.links
                        if link.id == StableId("mara-lantern")
                    )
                ),
                AddFact(expected.world.fact(StableId("lantern-found"))),
                GrantKnowledge(
                    next(
                        entry
                        for entry in expected.world.knowledge
                        if entry.fact_id == StableId("lantern-found")
                    )
                ),
                RecordEvent(
                    next(
                        event
                        for event in expected.story.events
                        if event.id == StableId("find-lantern")
                    )
                ),
            ),
        )
        assert store.commit(run_id, changes) == expected
        assert store.load(run_id, revision=StateRevision(1)) == initial
        assert store.load(run_id, revision=StateRevision(2)) == expected
        with pytest.raises(PersistenceConflictError):
            store.commit(
                run_id,
                ApprovedChangeSet(
                    proposal_id=StableId(f"stale-{uuid4()}"),
                    base_revision=StateRevision(1),
                ),
            )
        assert store.load(run_id) == expected
    finally:
        with connections.connect() as connection:
            with connection.transaction():
                connection.execute(
                    "DELETE FROM story_runs WHERE run_id = %s", (str(run_id),)
                )
