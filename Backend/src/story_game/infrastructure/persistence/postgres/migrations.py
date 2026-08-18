"""Small SQL migration runner for the PostgreSQL adapter."""

from __future__ import annotations

from pathlib import Path

from .connection import PostgresConnectionFactory


class PostgresSchemaMigrator:
    """Apply bundled, ordered SQL migrations exactly once per database."""

    def __init__(
        self,
        connections: PostgresConnectionFactory,
        migration_directory: Path | str | None = None,
    ) -> None:
        self.connections = connections
        self.migration_directory = (
            Path(migration_directory)
            if migration_directory is not None
            else Path(__file__).with_name("migrations")
        )

    def migrate(self) -> None:
        migrations = sorted(self.migration_directory.glob("*.sql"))
        with self.connections.connect() as connection:
            with connection.transaction():
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                applied = {
                    row["version"]
                    for row in connection.execute(
                        "SELECT version FROM schema_migrations"
                    ).fetchall()
                }
                for migration in migrations:
                    version = int(migration.name.split("_", 1)[0])
                    if version in applied:
                        continue
                    connection.execute(
                        migration.read_text(encoding="utf-8")
                    )
                    connection.execute(
                        "INSERT INTO schema_migrations (version) VALUES (%s)",
                        (version,),
                    )
