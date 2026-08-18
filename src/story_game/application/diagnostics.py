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
class RevisionConflict:
    """A write lost its expected-revision race."""

    detail: str
    run_id: str | None = None


DiagnosticEvent = (
    ModelCallFailed | SummaryGenerationFailed | ProposalRejected | RevisionConflict
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
    "ModelCallFailed",
    "NullDiagnosticsLog",
    "ProposalRejected",
    "RevisionConflict",
    "SummaryGenerationFailed",
]
