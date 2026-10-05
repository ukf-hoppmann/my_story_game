"""Keep tests that touch ``llm_task_settings`` away from the shared dev data."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from story_game.infrastructure.persistence.postgres import PostgresConnectionFactory


@contextmanager
def parked_model_settings(connections: PostgresConnectionFactory) -> Iterator[None]:
    """Run with an empty ``llm_task_settings`` table, then put the real rows back.

    The table lives in the same database as the dev stack. Without this, a
    test that starts the app (which seeds the table from *its* ``llm.toml``)
    would leave foreign model references behind, and a test that expects the
    seed would see the developer's own rows.
    """
    with connections.connect() as connection:
        saved = connection.execute("SELECT * FROM llm_task_settings").fetchall()
        connection.execute("DELETE FROM llm_task_settings")
        connection.commit()
    try:
        yield
    finally:
        with connections.connect() as connection:
            connection.execute("DELETE FROM llm_task_settings")
            for row in saved:
                columns = ", ".join(row)
                placeholders = ", ".join(["%s"] * len(row))
                connection.execute(
                    f"INSERT INTO llm_task_settings ({columns}) VALUES ({placeholders})",
                    list(row.values()),
                )
            connection.commit()
