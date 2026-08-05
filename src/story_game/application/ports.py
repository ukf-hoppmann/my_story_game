"""Persistence ports owned by the application layer."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from story_game.domain import ApprovedChangeSet, GameState, StableId, StateRevision


class GameStateStoreError(Exception):
    """Base failure exposed by the canonical-state persistence port."""


class GameStateNotFoundError(GameStateStoreError):
    """The requested run or revision does not exist."""


class GameStateConflictError(GameStateStoreError):
    """A canonical-state write lost its concurrency race."""


class GameStateConsistencyError(GameStateStoreError):
    """Stored data cannot be reconstructed as a valid domain state."""


class GameStateReader(Protocol):
    """Load one canonical game-state revision."""

    def load(
        self,
        run_id: StableId,
        *,
        revision: StateRevision | None = None,
    ) -> GameState: ...


class GameStateWriter(Protocol):
    """Create or atomically advance one canonical game-state stream."""

    def create_initial(self, state: GameState) -> None: ...

    def commit(
        self,
        run_id: StableId,
        changes: ApprovedChangeSet,
    ) -> GameState: ...


class GameStateStore(GameStateReader, GameStateWriter, Protocol):
    """Combined canonical-state port for adapters supporting reads and writes."""


class GameStateDocumentCodec(Protocol):
    """Translate canonical state documents without coupling consumers to JSON."""

    def decode(self, document: Mapping[str, object]) -> GameState: ...

    def encode(self, state: GameState) -> dict[str, object]: ...
