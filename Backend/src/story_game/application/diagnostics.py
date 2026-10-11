"""Application-owned diagnostics port: typed critical events plus debug tracing.

TASK-024 splits diagnostics into two deliberately different shapes:

- ``record()`` carries a closed, typed ``DiagnosticEvent`` union. Every
  variant's schema only ever holds safe, structured metadata — never player
  prose, prompts, or raw provider payloads — so it stays safe to render in
  every profile, including production, without runtime filtering. This is
  the "mindestens fehlgeschlagene Modellaufrufe, verworfene
  Änderungsvorschläge und Revisionskonflikte sind sichtbar" half of
  TASK-024's completion criteria.
- ``trace()`` is the deliberate opposite: an unrestricted, generic
  key/value call meant for excessive development tracing of transformed
  data at each operation boundary, so a transformation bug (not just a
  model or persistence failure) is visible too. Callers may pass anything,
  including full prose — an infrastructure adapter decides per configured
  profile whether a given call renders at all, so application code never
  needs to guard the call itself or know which profile is active.

Domain code never calls either method; the Application layer decides what
is diagnostically relevant, and an infrastructure adapter wired at the
composition root decides how it is rendered and where it goes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from story_game.application.llm.contracts import LLMError


@dataclass(frozen=True, slots=True)
class ModelCallFailed:
    """A configured model call returned an expected, typed failure."""

    task: str
    error: LLMError
    run_id: str | None = None


@dataclass(frozen=True, slots=True)
class SummaryGenerationFailed:
    """The rolling summary could not be produced; the turn commits regardless.

    Kept distinct from ``ModelCallFailed`` because a failed summary call
    deliberately does not fail the turn (see TASK-023) — a reader of the
    log needs to tell the two situations apart without inspecting ``task``.
    """

    error: LLMError
    run_id: str | None = None


@dataclass(frozen=True, slots=True)
class ProposalRejected:
    """A turn or initialization proposal was discarded as a whole.

    ``reason`` is a short, developer-authored category string (e.g. an
    error kind or exception type name), never the proposal's own content.
    """

    reason: str
    run_id: str | None = None


@dataclass(frozen=True, slots=True)
class ProposalItemDropped:
    """One item of a turn proposal was dropped, the rest went on.

    Temporary workaround (TASK-042) for models that invent references; the
    ``reason`` names the unresolvable reference, never the proposal's content.
    """

    reason: str
    run_id: str | None = None


@dataclass(frozen=True, slots=True)
class RevisionConflict:
    """A write lost its expected-revision race."""

    detail: str
    run_id: str | None = None


@dataclass(frozen=True, slots=True)
class WorldTrackingSettingUnavailable:
    """The world-tracking switch could not be read; the game kept tracking."""


@dataclass(frozen=True, slots=True)
class FrontendToolingError:
    """A frontend-side failure that never reached the backend as a typed API
    error (TASK-030): a network failure, a JSON-parse failure, or a
    synchronous JS exception thrown before a request was even dispatched.

    Reported by the frontend itself via a dedicated, authenticated endpoint
    (``POST /api/v1/diagnostics/frontend-errors``) — deliberately excluding
    ``401``s, which the frontend handles as a forced re-login instead, since
    at that point no valid token remains to authenticate the report with.
    ``source`` is a short, developer-authored label identifying the call
    site (e.g. ``"wizard.handleCreateProposal"``), never free text; ``message``
    is the underlying JS/browser error text, bounded by the API schema.
    """

    source: str
    message: str
    url: str | None = None
    user_agent: str | None = None


DiagnosticEvent = (
    ModelCallFailed
    | SummaryGenerationFailed
    | ProposalRejected
    | ProposalItemDropped
    | RevisionConflict
    | WorldTrackingSettingUnavailable
    | FrontendToolingError
)


class DiagnosticsLog(Protocol):
    """Narrow application-owned diagnostics boundary, implemented by infrastructure."""

    def record(self, event: DiagnosticEvent) -> None:
        """Emit a closed, typed, production-safe diagnostic event."""
        ...

    def trace(self, step: str, **fields: object) -> None:
        """Emit an unrestricted development-tracing event, active only in debug profiles."""
        ...


class NullDiagnosticsLog:
    """A ``DiagnosticsLog`` that discards everything.

    Used as the default so existing callers and tests are not forced to
    wire a real adapter everywhere logging is not the point of the test.
    """

    def record(self, event: DiagnosticEvent) -> None:  # noqa: D102 - Protocol impl
        return None

    def trace(self, step: str, **fields: object) -> None:  # noqa: D102 - Protocol impl
        return None


__all__ = [
    "DiagnosticEvent",
    "DiagnosticsLog",
    "FrontendToolingError",
    "ModelCallFailed",
    "NullDiagnosticsLog",
    "ProposalItemDropped",
    "ProposalRejected",
    "RevisionConflict",
    "SummaryGenerationFailed",
    "WorldTrackingSettingUnavailable",
]
