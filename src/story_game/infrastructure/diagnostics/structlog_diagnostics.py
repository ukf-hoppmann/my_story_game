"""structlog-backed implementation of the application's ``DiagnosticsLog`` port."""

from __future__ import annotations

import structlog

from story_game.application.diagnostics import (
    DiagnosticEvent,
    ModelCallFailed,
    ProposalRejected,
    RevisionConflict,
    SummaryGenerationFailed,
)

_logger = structlog.get_logger("story_game.diagnostics")


class StructlogDiagnosticsLog:
    """Renders ``record()`` always; renders ``trace()`` only in debug profiles.

    ``debug_enabled`` is an explicit constructor flag, not a check against
    the configured structlog level — a belt-and-suspenders guard so that a
    misconfigured verbosity in production cannot, by itself, start emitting
    the unrestricted development trace.
    """

    def __init__(self, *, debug_enabled: bool) -> None:
        self._debug_enabled = debug_enabled

    def record(self, event: DiagnosticEvent) -> None:
        event_name, level, fields = _render(event)
        log = _logger.bind(**fields)
        if level == "error":
            log.error(event_name)
        else:
            log.warning(event_name)

    def trace(self, step: str, **fields: object) -> None:
        if not self._debug_enabled:
            return
        _logger.debug(step, **fields)


def _render(event: DiagnosticEvent) -> tuple[str, str, dict[str, object]]:
    if isinstance(event, ModelCallFailed):
        fields = {
            "task": event.task,
            "error_kind": event.error.kind.value,
            "error_message": event.error.message,
            "retryable": event.error.retryable,
            "run_id": event.run_id,
        }
        level = "warning" if event.error.retryable else "error"
        return "model_call_failed", level, fields
    if isinstance(event, SummaryGenerationFailed):
        fields = {
            "error_kind": event.error.kind.value,
            "error_message": event.error.message,
            "retryable": event.error.retryable,
            "run_id": event.run_id,
        }
        return "summary_generation_failed", "warning", fields
    if isinstance(event, ProposalRejected):
        return (
            "proposal_rejected",
            "warning",
            {"reason": event.reason, "run_id": event.run_id},
        )
    if isinstance(event, RevisionConflict):
        return (
            "revision_conflict",
            "warning",
            {"detail": event.detail, "run_id": event.run_id},
        )
    raise TypeError(f"Unbekanntes DiagnosticEvent: {type(event).__name__}")


__all__ = ["StructlogDiagnosticsLog"]
