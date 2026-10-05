"""PostgreSQL adapter for versioned system prompts and the catalog built on it."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import psycopg

from story_game.application.llm import (
    InvalidPromptPackageError,
    PromptPackage,
    PromptPackageCatalog,
    PromptPackageNotFoundError,
)
from story_game.application.prompt_management import (
    NewPromptVersion,
    PromptEntry,
    PromptEntryKind,
    PromptOptionUsage,
    PromptStoreError,
    PromptVersion,
    PromptVersionReader,
    PromptVersionSource,
    PromptVersionWriter,
    assemble_package,
)
from story_game.domain import StableId

from .connection import PostgresConnectionFactory

_COLUMNS = """
    version_id, package_id, package_version, entry_kind, entry_key, entry_text,
    sort_position, is_default, task_ids, source, created_at, created_by, is_active
"""
_KIND_ORDER = """
    CASE entry_kind WHEN 'task' THEN 0 WHEN 'option' THEN 1 ELSE 2 END
"""


class PostgresPromptStore(PromptVersionReader, PromptVersionWriter):
    def __init__(self, connections: PostgresConnectionFactory) -> None:
        self._connections = connections

    def list_active(self, package_id: str, package_version: str) -> tuple[PromptVersion, ...]:
        return self._query(
            f"""
            SELECT {_COLUMNS} FROM system_prompts
            WHERE package_id = %s AND package_version = %s AND is_active
            ORDER BY {_KIND_ORDER}, sort_position
            """,
            (package_id, package_version),
            "Die aktiven Prompts konnten nicht gelesen werden",
        )

    def list_archived(self, package_id: str, package_version: str) -> tuple[PromptVersion, ...]:
        return self._query(
            f"""
            SELECT DISTINCT ON (entry_kind, entry_key) {_COLUMNS} FROM system_prompts AS row
            WHERE package_id = %s AND package_version = %s
              AND NOT EXISTS (
                  SELECT 1 FROM system_prompts AS other
                  WHERE other.package_id = row.package_id
                    AND other.package_version = row.package_version
                    AND other.entry_kind = row.entry_kind
                    AND other.entry_key = row.entry_key
                    AND other.is_active
              )
            ORDER BY entry_kind, entry_key, created_at DESC
            """,
            (package_id, package_version),
            "Der Papierkorb konnte nicht gelesen werden",
        )

    def list_history(
        self, package_id: str, package_version: str, kind: PromptEntryKind, key: str
    ) -> tuple[PromptVersion, ...]:
        return self._query(
            f"""
            SELECT {_COLUMNS} FROM system_prompts
            WHERE package_id = %s AND package_version = %s
              AND entry_kind = %s AND entry_key = %s
            ORDER BY created_at DESC, is_active DESC
            """,
            (package_id, package_version, kind.value, key),
            "Die Prompt-Historie konnte nicht gelesen werden",
        )

    def append_versions(self, versions: Sequence[NewPromptVersion]) -> tuple[PromptVersion, ...]:
        try:
            with self._connections.connect() as connection:
                with connection.transaction():
                    created = [self._append(connection, version) for version in versions]
        except psycopg.Error as error:
            raise PromptStoreError("Die Prompts konnten nicht gespeichert werden") from error
        return tuple(created)

    @staticmethod
    def _append(connection: psycopg.Connection[Any], version: NewPromptVersion) -> PromptVersion:
        entry = version.entry
        connection.execute(
            """
            UPDATE system_prompts SET is_active = FALSE
            WHERE package_id = %s AND package_version = %s
              AND entry_kind = %s AND entry_key = %s AND is_active
            """,
            (version.package_id, version.package_version, entry.kind.value, entry.key),
        )
        row = connection.execute(
            f"""
            INSERT INTO system_prompts (
                version_id, package_id, package_version, entry_kind, entry_key,
                entry_text, sort_position, is_default, task_ids, source,
                created_at, created_by, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            RETURNING {_COLUMNS}
            """,
            (
                version.version_id.value,
                version.package_id,
                version.package_version,
                entry.kind.value,
                entry.key,
                entry.text,
                entry.position,
                entry.is_default,
                list(entry.task_ids),
                version.source.value,
                version.created_at,
                version.created_by,
            ),
        ).fetchone()
        assert row is not None
        return _version(row)

    def deactivate_entry(
        self, package_id: str, package_version: str, kind: PromptEntryKind, key: str
    ) -> None:
        try:
            with self._connections.connect() as connection:
                connection.execute(
                    """
                    UPDATE system_prompts SET is_active = FALSE
                    WHERE package_id = %s AND package_version = %s
                      AND entry_kind = %s AND entry_key = %s AND is_active
                    """,
                    (package_id, package_version, kind.value, key),
                )
        except psycopg.Error as error:
            raise PromptStoreError("Der Prompt-Eintrag konnte nicht entfernt werden") from error

    def restore_entry(
        self, package_id: str, package_version: str, kind: PromptEntryKind, key: str
    ) -> None:
        try:
            with self._connections.connect() as connection:
                connection.execute(
                    """
                    UPDATE system_prompts SET is_active = TRUE
                    WHERE version_id = (
                        SELECT version_id FROM system_prompts
                        WHERE package_id = %s AND package_version = %s
                          AND entry_kind = %s AND entry_key = %s
                        ORDER BY created_at DESC LIMIT 1
                    )
                    AND NOT EXISTS (
                        SELECT 1 FROM system_prompts
                        WHERE package_id = %s AND package_version = %s
                          AND entry_kind = %s AND entry_key = %s AND is_active
                    )
                    """,
                    (package_id, package_version, kind.value, key) * 2,
                )
        except psycopg.Error as error:
            raise PromptStoreError("Der Prompt-Eintrag konnte nicht wiederhergestellt werden") from error

    def purge_entry(
        self, package_id: str, package_version: str, kind: PromptEntryKind, key: str
    ) -> None:
        try:
            with self._connections.connect() as connection:
                connection.execute(
                    """
                    DELETE FROM system_prompts
                    WHERE package_id = %s AND package_version = %s
                      AND entry_kind = %s AND entry_key = %s
                      AND NOT EXISTS (
                          SELECT 1 FROM system_prompts AS active
                          WHERE active.package_id = %s AND active.package_version = %s
                            AND active.entry_kind = %s AND active.entry_key = %s
                            AND active.is_active
                      )
                    """,
                    (package_id, package_version, kind.value, key) * 2,
                )
        except psycopg.Error as error:
            raise PromptStoreError("Der Prompt-Eintrag konnte nicht gelöscht werden") from error

    def _query(self, sql: str, params: tuple[Any, ...], failure: str) -> tuple[PromptVersion, ...]:
        try:
            with self._connections.connect() as connection:
                return tuple(_version(row) for row in connection.execute(sql, params).fetchall())
        except psycopg.Error as error:
            raise PromptStoreError(failure) from error


# The configuration column that holds the selection of each extensible category.
_OPTION_COLUMNS = {"genre": "genre", "tone": "tone", "prose_style": "prose_style"}


class PostgresPromptOptionUsage(PromptOptionUsage):
    """Whether any stored game revision still selects an option."""

    def __init__(self, connections: PostgresConnectionFactory) -> None:
        self._connections = connections

    def is_option_used(self, category_id: str, option_id: str) -> bool:
        column = _OPTION_COLUMNS.get(category_id)
        if column is None:
            raise PromptStoreError(f"Die Kategorie {category_id!r} kennt keine Nutzungsprüfung")
        try:
            with self._connections.connect() as connection:
                row = connection.execute(
                    f"SELECT EXISTS (SELECT 1 FROM game_state_configurations WHERE {column} = %s) AS used",  # noqa: S608 - column comes from the fixed mapping above
                    (option_id,),
                ).fetchone()
        except psycopg.Error as error:
            raise PromptStoreError("Die Nutzung der Option konnte nicht geprüft werden") from error
        return bool(row and row["used"])


class DbPromptPackageCatalog(PromptPackageCatalog):
    """Loads the active prompts of a package from the store; same contract as the TOML catalog."""

    def __init__(self, reader: PromptVersionReader) -> None:
        self._reader = reader

    def load(self, package_id: str, version: str) -> PromptPackage:
        try:
            active = self._reader.list_active(package_id, version)
        except PromptStoreError as error:
            raise InvalidPromptPackageError(
                f"Das Prompt-Paket {package_id!r} in Version {version!r} konnte nicht gelesen werden"
            ) from error
        if not active:
            raise PromptPackageNotFoundError(
                f"Das Prompt-Paket {package_id!r} in Version {version!r} wurde nicht gefunden"
            )
        return assemble_package(package_id, version, tuple(row.entry for row in active))


def _version(row: dict[str, Any]) -> PromptVersion:
    return PromptVersion(
        version_id=StableId(row["version_id"]),
        package_id=row["package_id"],
        package_version=row["package_version"],
        entry=PromptEntry(
            kind=PromptEntryKind(row["entry_kind"]),
            key=row["entry_key"],
            text=row["entry_text"],
            position=int(row["sort_position"]),
            is_default=bool(row["is_default"]),
            task_ids=tuple(row["task_ids"]),
        ),
        source=PromptVersionSource(row["source"]),
        created_at=row["created_at"],
        created_by=row["created_by"],
        is_active=bool(row["is_active"]),
    )


__all__ = ["DbPromptPackageCatalog", "PostgresPromptOptionUsage", "PostgresPromptStore"]
