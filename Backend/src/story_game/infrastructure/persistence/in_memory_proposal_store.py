"""In-process, TTL-expiring implementation of ``InitialProposalStore``.

A run proposal only needs to survive between one ``ProposeGameRun`` call and
the matching ``ConfirmGameRunProposal`` call a few minutes later — it is
never canonical persistence. A plain in-memory dict with a TTL is therefore
enough for the current single-instance backend deployment (see
``compose.yaml`` — no Redis or similar shared cache is provisioned). This is
a genuine limitation: a second backend instance would not see proposals
created on the first. Should the deployment ever become multi-instance, this
adapter can be swapped for a shared-cache implementation of the same
``InitialProposalStore`` port without changing any Application code.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from story_game.application.game_models import CachedGameRunProposal
from story_game.domain import StableId

DEFAULT_PROPOSAL_TTL = timedelta(minutes=30)


@dataclass(frozen=True, slots=True)
class _Entry:
    proposal: CachedGameRunProposal
    expires_at: datetime


class InMemoryProposalStore:
    def __init__(
        self,
        *,
        ttl: timedelta = DEFAULT_PROPOSAL_TTL,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._ttl = ttl
        self._now = now
        self._lock = threading.Lock()
        self._entries: dict[StableId, _Entry] = {}

    def save(self, proposal_id: StableId, proposal: CachedGameRunProposal) -> None:
        with self._lock:
            self._entries[proposal_id] = _Entry(proposal, self._now() + self._ttl)

    def load(self, proposal_id: StableId) -> CachedGameRunProposal | None:
        with self._lock:
            entry = self._entries.get(proposal_id)
            if entry is None:
                return None
            if entry.expires_at <= self._now():
                del self._entries[proposal_id]
                return None
            return entry.proposal

    def delete(self, proposal_id: StableId) -> None:
        with self._lock:
            self._entries.pop(proposal_id, None)
