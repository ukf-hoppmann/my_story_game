"""Atomic writer for versioned JSON game-state snapshots."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from story_game.domain import GameState
from story_game.infrastructure.persistence.errors import PersistenceError

from .mapper import state_to_document


class JsonStateWriter:
    """Write one deterministic snapshot without exposing partial files."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def save(self, state: GameState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary_path = stream.name
                json.dump(
                    state_to_document(state),
                    stream,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, self.path)
            temporary_path = None
        except OSError as exc:
            raise PersistenceError(f"JSON-State konnte nicht gespeichert werden: {self.path}") from exc
        finally:
            if temporary_path is not None:
                try:
                    os.unlink(temporary_path)
                except OSError:
                    pass
