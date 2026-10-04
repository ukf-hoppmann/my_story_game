"""PostgreSQL adapter for scene images (``SceneImageWriter``/``SceneImageReader``).

Reads join the run's members, so a caller outside the run gets the same
empty result as for a missing image.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg

from story_game.application.scene_image import (
    NewSceneImage,
    SceneImageContent,
    SceneImageReader,
    SceneImageRecord,
    SceneImageStatus,
    SceneImageStoreError,
    SceneImageWriter,
)
from story_game.domain import StableId

from .connection import PostgresConnectionFactory

_RECORD_COLUMNS = """
    s.image_id, s.run_id, s.turn_sequence, s.status, s.model, s.refine,
    s.refine_model, s.refine_strength, s.width, s.height, s.seed, s.prompt,
    s.compact_prompt, s.error_message, s.created_at, s.completed_at
"""
_MEMBER_JOIN = """
    JOIN game_run_members m
      ON m.run_id = s.run_id AND m.issuer = %s AND m.subject = %s
"""


class PostgresSceneImageStore(SceneImageWriter, SceneImageReader):
    def __init__(self, connections: PostgresConnectionFactory) -> None:
        self._connections = connections

    def create_pending(self, image: NewSceneImage) -> SceneImageRecord:
        options = image.options
        row = self._one(
            f"""
            INSERT INTO scene_images AS s (
                image_id, run_id, turn_sequence, status, model, refine,
                refine_model, refine_strength, width, height, seed, created_at
            ) VALUES (%s, %s, %s, 'pending', %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING {_RECORD_COLUMNS}
            """,
            (
                image.image_id.value,
                image.run_id.value,
                image.turn_sequence,
                options.model,
                options.refine,
                options.refine_model,
                options.refine_strength,
                options.width,
                options.height,
                options.seed,
                image.created_at,
            ),
            "Das Szenenbild konnte nicht angelegt werden",
        )
        return _record(row)

    def find_active(
        self, run_id: StableId, turn_sequence: int, *, created_after: datetime
    ) -> SceneImageRecord | None:
        row = self._one(
            f"""
            SELECT {_RECORD_COLUMNS} FROM scene_images s
            WHERE s.run_id = %s AND s.turn_sequence = %s
              AND s.status = 'pending' AND s.created_at > %s
            ORDER BY s.created_at DESC LIMIT 1
            """,
            (run_id.value, turn_sequence, created_after),
            "Das laufende Szenenbild konnte nicht geprüft werden",
        )
        return None if row is None else _record(row)

    def save_prompts(
        self, image_id: StableId, prompt: str, compact_prompt: str | None
    ) -> None:
        self._execute(
            "UPDATE scene_images SET prompt = %s, compact_prompt = %s WHERE image_id = %s",
            (prompt, compact_prompt, image_id.value),
            "Der Bildprompt konnte nicht gespeichert werden",
        )

    def complete(
        self, image_id: StableId, content: SceneImageContent, completed_at: datetime
    ) -> None:
        self._execute(
            """
            UPDATE scene_images
            SET status = 'ready', image = %s, content_type = %s,
                error_message = NULL, completed_at = %s
            WHERE image_id = %s
            """,
            (content.data, content.content_type, completed_at, image_id.value),
            "Das Bild konnte nicht gespeichert werden",
        )

    def fail(self, image_id: StableId, message: str, completed_at: datetime) -> None:
        self._execute(
            """
            UPDATE scene_images
            SET status = 'failed', error_message = %s, completed_at = %s
            WHERE image_id = %s
            """,
            (message, completed_at, image_id.value),
            "Der Bildfehler konnte nicht gespeichert werden",
        )

    def get(
        self, run_id: StableId, image_id: StableId, issuer: str, subject: str
    ) -> SceneImageRecord | None:
        row = self._one(
            f"""
            SELECT {_RECORD_COLUMNS} FROM scene_images s {_MEMBER_JOIN}
            WHERE s.run_id = %s AND s.image_id = %s
            """,
            (issuer, subject, run_id.value, image_id.value),
            "Das Szenenbild konnte nicht geladen werden",
        )
        return None if row is None else _record(row)

    def list_for_run(
        self, run_id: StableId, issuer: str, subject: str, limit: int
    ) -> tuple[SceneImageRecord, ...]:
        rows = self._all(
            f"""
            SELECT {_RECORD_COLUMNS} FROM scene_images s {_MEMBER_JOIN}
            WHERE s.run_id = %s
            ORDER BY s.created_at DESC, s.image_id LIMIT %s
            """,
            (issuer, subject, run_id.value, limit),
            "Die Szenenbilder konnten nicht geladen werden",
        )
        return tuple(_record(row) for row in rows)

    def load_content(
        self, run_id: StableId, image_id: StableId, issuer: str, subject: str
    ) -> SceneImageContent | None:
        row = self._one(
            f"""
            SELECT s.image, s.content_type FROM scene_images s {_MEMBER_JOIN}
            WHERE s.run_id = %s AND s.image_id = %s AND s.status = 'ready'
            """,
            (issuer, subject, run_id.value, image_id.value),
            "Das Bild konnte nicht geladen werden",
        )
        if row is None:
            return None
        return SceneImageContent(bytes(row["image"]), str(row["content_type"]))

    def _one(self, sql: str, params: tuple[Any, ...], failure: str) -> dict[str, Any] | None:
        try:
            with self._connections.connect() as connection:
                row = connection.execute(sql, params).fetchone()
                connection.commit()
                return row
        except psycopg.Error as error:
            raise SceneImageStoreError(failure) from error

    def _all(self, sql: str, params: tuple[Any, ...], failure: str) -> list[dict[str, Any]]:
        try:
            with self._connections.connect() as connection:
                return connection.execute(sql, params).fetchall()
        except psycopg.Error as error:
            raise SceneImageStoreError(failure) from error

    def _execute(self, sql: str, params: tuple[Any, ...], failure: str) -> None:
        try:
            with self._connections.connect() as connection:
                connection.execute(sql, params)
                connection.commit()
        except psycopg.Error as error:
            raise SceneImageStoreError(failure) from error


def _record(row: dict[str, Any]) -> SceneImageRecord:
    return SceneImageRecord(
        image_id=StableId(row["image_id"]),
        run_id=StableId(row["run_id"]),
        turn_sequence=int(row["turn_sequence"]),
        status=SceneImageStatus(str(row["status"])),
        model=row["model"],
        refine=bool(row["refine"]),
        refine_model=row["refine_model"],
        refine_strength=float(row["refine_strength"]),
        width=int(row["width"]),
        height=int(row["height"]),
        seed=int(row["seed"]),
        created_at=row["created_at"],
        prompt=row["prompt"],
        compact_prompt=row["compact_prompt"],
        error_message=row["error_message"],
        completed_at=row["completed_at"],
    )


__all__ = ["PostgresSceneImageStore"]
