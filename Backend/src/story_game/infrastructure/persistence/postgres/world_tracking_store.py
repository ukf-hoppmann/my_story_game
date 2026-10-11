"""PostgreSQL adapter for the global world-tracking switch."""

from __future__ import annotations

import psycopg

from story_game.application.world_tracking import (
    WorldTrackingSetting,
    WorldTrackingSettingReader,
    WorldTrackingSettingWriter,
    WorldTrackingStoreError,
)

from .connection import PostgresConnectionFactory


class PostgresWorldTrackingStore(WorldTrackingSettingReader, WorldTrackingSettingWriter):
    def __init__(self, connections: PostgresConnectionFactory) -> None:
        self._connections = connections

    def load(self) -> WorldTrackingSetting | None:
        try:
            with self._connections.connect() as connection:
                row = connection.execute(
                    "SELECT enabled, updated_at, updated_by FROM world_tracking_setting"
                ).fetchone()
        except psycopg.Error as error:
            raise WorldTrackingStoreError(
                "Die Einstellung zum Welt-Tracking konnte nicht gelesen werden"
            ) from error
        if row is None:
            return None
        return WorldTrackingSetting(row["enabled"], row["updated_at"], row["updated_by"])

    def save(self, setting: WorldTrackingSetting) -> WorldTrackingSetting:
        try:
            with self._connections.connect() as connection:
                with connection.transaction():
                    connection.execute(
                        """
                        INSERT INTO world_tracking_setting (id, enabled, updated_at, updated_by)
                        VALUES (TRUE, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            enabled = EXCLUDED.enabled,
                            updated_at = EXCLUDED.updated_at,
                            updated_by = EXCLUDED.updated_by
                        """,
                        (setting.enabled, setting.updated_at, setting.updated_by),
                    )
        except psycopg.Error as error:
            raise WorldTrackingStoreError(
                "Die Einstellung zum Welt-Tracking konnte nicht gespeichert werden"
            ) from error
        return setting


__all__ = ["PostgresWorldTrackingStore"]
