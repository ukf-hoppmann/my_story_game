"""Transient model-independent change proposals awaiting application review."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from story_game.domain.changes import StateOperation
from story_game.domain.value_objects import Evidence, StableId, StateRevision, Visibility


class ProposalStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True, slots=True)
class ProposedChange:
    """One untrusted typed suggestion with its supporting evidence."""

    id: StableId
    operation: StateOperation
    evidence: Evidence
    visibility: Visibility


@dataclass(frozen=True, slots=True)
class ProposedChangeSet:
    """Transient suggestions that never become canonical persistence records."""

    id: StableId
    base_revision: StateRevision
    changes: tuple[ProposedChange, ...] = ()
    status: ProposalStatus = ProposalStatus.PENDING
