"""PostgreSQL adapter for the versioned per-task model settings."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import psycopg

from story_game.application.llm import GenerationTask
from story_game.application.model_settings import (
    ModelSettingsReader,
    ModelSettingsStoreError,
    ModelSettingsWriter,
    ModelSettingSource,
    ModelSettingVersion,
    NewModelSettingVersion,
    TaskModelSetting,
)
from story_game.domain import StableId

from .connection import PostgresConnectionFactory

_COLUMNS = """
    version_id, task, model_ref, temperature, max_output_tokens, source,
    created_at, created_by, is_active
"""


class PostgresModelSettingsStore(ModelSettingsReader, ModelSettingsWriter):
    def __init__(self, connections: PostgresConnectionFactory) -> None:
        self._connections = connections

    def list_active(self) -> tuple[ModelSettingVersion, ...]:
        return self._query(
            f"SELECT {_COLUMNS} FROM llm_task_settings WHERE is_active",
            (),
            "Die aktiven Modelleinstellungen konnten nicht gelesen werden",
        )

    def list_history(self, task: GenerationTask) -> tuple[ModelSettingVersion, ...]:
        return self._query(
            f"""
            SELECT {_COLUMNS} FROM llm_task_settings
            WHERE task = %s
            ORDER BY created_at DESC, is_active DESC
            """,
            (task.value,),
            "Der Verlauf der Modelleinstellung konnte nicht gelesen werden",
        )

    def append_versions(
        self, versions: Sequence[NewModelSettingVersion]
    ) -> tuple[ModelSettingVersion, ...]:
        try:
            with self._connections.connect() as connection:
                with connection.transaction():
                    created = [self._append(connection, version) for version in versions]
        except psycopg.Error as error:
            raise ModelSettingsStoreError(
                "Die Modelleinstellungen konnten nicht gespeichert werden"
            ) from error
        return tuple(created)

    @staticmethod
    def _append(
        connection: psycopg.Connection[Any], version: NewModelSettingVersion
    ) -> ModelSettingVersion:
        setting = version.setting
        connection.execute(
            "UPDATE llm_task_settings SET is_active = FALSE WHERE task = %s AND is_active",
            (setting.task.value,),
        )
        row = connection.execute(
            f"""
            INSERT INTO llm_task_settings (
                version_id, task, model_ref, temperature, max_output_tokens,
                source, created_at, created_by, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            RETURNING {_COLUMNS}
            """,
            (
                version.version_id.value,
                setting.task.value,
                setting.model_ref,
                setting.temperature,
                setting.max_output_tokens,
                version.source.value,
                version.created_at,
                version.created_by,
            ),
        ).fetchone()
        assert row is not None
        return _version(row)

    def _query(
        self, sql: str, params: tuple[Any, ...], failure: str
    ) -> tuple[ModelSettingVersion, ...]:
        try:
            with self._connections.connect() as connection:
                return tuple(_version(row) for row in connection.execute(sql, params).fetchall())
        except psycopg.Error as error:
            raise ModelSettingsStoreError(failure) from error


def _version(row: dict[str, Any]) -> ModelSettingVersion:
    return ModelSettingVersion(
        version_id=StableId(row["version_id"]),
        setting=TaskModelSetting(
            task=GenerationTask(row["task"]),
            model_ref=row["model_ref"],
            temperature=row["temperature"],
            max_output_tokens=row["max_output_tokens"],
        ),
        source=ModelSettingSource(row["source"]),
        created_at=row["created_at"],
        created_by=row["created_by"],
        is_active=bool(row["is_active"]),
    )


__all__ = ["PostgresModelSettingsStore"]
