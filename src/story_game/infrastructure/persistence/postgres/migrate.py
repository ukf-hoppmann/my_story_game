"""Command-line entry point for applying the bundled PostgreSQL schema."""

from __future__ import annotations

import os

from .connection import PostgresConnectionFactory
from .migrations import PostgresSchemaMigrator


def main() -> None:
    dsn = os.environ.get("STORY_GAME_POSTGRES_DSN")
    if not dsn:
        raise SystemExit("STORY_GAME_POSTGRES_DSN ist nicht gesetzt")
    PostgresSchemaMigrator(PostgresConnectionFactory(dsn)).migrate()


if __name__ == "__main__":
    main()
