from __future__ import annotations

from datetime import UTC, datetime

import pytest

pytest.importorskip("psycopg")

from story_game.application.world_tracking import WorldTrackingSetting  # noqa: E402
from tests.persistence.test_postgres_persistence import postgres_store  # noqa: E402,F401

EDITED = datetime(2026, 10, 11, 12, tzinfo=UTC)


@pytest.fixture
def tracking_store(postgres_store):  # noqa: F811
    """The store on an empty table; the developer's own row is put back after."""
    from story_game.infrastructure.persistence.postgres import PostgresWorldTrackingStore

    _, connections = postgres_store
    with connections.connect() as connection:
        saved = connection.execute("SELECT * FROM world_tracking_setting").fetchall()
        connection.execute("DELETE FROM world_tracking_setting")
        connection.commit()
    try:
        yield PostgresWorldTrackingStore(connections)
    finally:
        with connections.connect() as connection:
            connection.execute("DELETE FROM world_tracking_setting")
            for row in saved:
                connection.execute(
                    "INSERT INTO world_tracking_setting (id, enabled, updated_at, updated_by)"
                    " VALUES (%s, %s, %s, %s)",
                    (row["id"], row["enabled"], row["updated_at"], row["updated_by"]),
                )
            connection.commit()


def test_an_empty_table_has_no_stored_setting(tracking_store) -> None:
    assert tracking_store.load() is None


def test_saving_twice_keeps_one_row_with_the_latest_value(tracking_store) -> None:
    tracking_store.save(WorldTrackingSetting(False, EDITED, "testadmin"))
    tracking_store.save(WorldTrackingSetting(True, EDITED, "otheradmin"))

    assert tracking_store.load() == WorldTrackingSetting(True, EDITED, "otheradmin")
