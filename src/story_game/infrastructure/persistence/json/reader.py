"""File reader for versioned JSON game-state snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from story_game.domain import GameState
from story_game.infrastructure.persistence.errors import PersistenceError

from .mapper import state_from_document


class JsonStateReader:
    """Read and validate one complete state snapshot from a JSON file."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def load(self) -> GameState:
        try:
            with self.path.open("r", encoding="utf-8") as stream:
                document: Any = json.load(stream)
        except (OSError, json.JSONDecodeError) as exc:
            raise PersistenceError(f"JSON-State konnte nicht gelesen werden: {self.path}") from exc
        return state_from_document(document)
