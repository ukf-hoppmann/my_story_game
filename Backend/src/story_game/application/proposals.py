"""Transient model-independent change proposals awaiting application review."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from story_game.domain.changes import StateOperation
from story_game.domain.value_objects import StableId, StateRevision, Visibility


class ProposalStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True, slots=True)
class ProposalEvidence:
    """Transient source context available only while reviewing a proposal."""

    source: str
    reference: str | None = None
    excerpt: str | None = None

    def __post_init__(self) -> None:
        source = self.source.strip()
        if not source:
            raise ValueError("Vorschlagsevidenz benötigt eine Quellenangabe")
        object.__setattr__(self, "source", source)
        if self.reference is not None:
            reference = self.reference.strip()
            object.__setattr__(self, "reference", reference or None)
        if self.excerpt is not None:
            excerpt = self.excerpt.strip()
            object.__setattr__(self, "excerpt", excerpt or None)


@dataclass(frozen=True, slots=True)
class ProposedChange:
    """One untrusted typed suggestion with its supporting evidence."""

    id: StableId
    operation: StateOperation
    evidence: ProposalEvidence
    visibility: Visibility


@dataclass(frozen=True, slots=True)
class ProposedChangeSet:
    """Transient suggestions that never become canonical persistence records."""

    id: StableId
    base_revision: StateRevision
    changes: tuple[ProposedChange, ...] = ()
    status: ProposalStatus = ProposalStatus.PENDING
