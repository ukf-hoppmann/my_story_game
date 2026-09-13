"""Verify the structlog-backed ``DiagnosticsLog`` adapter's redaction contract."""

from __future__ import annotations

import dataclasses
import logging

import structlog
from structlog.testing import LogCapture

from story_game.application.diagnostics import (
    DiagnosticEvent,
    FrontendToolingError,
    ModelCallFailed,
    ProposalRejected,
    RevisionConflict,
    SummaryGenerationFailed,
)
from story_game.application.llm import LLMError, LLMErrorKind
from story_game.infrastructure.diagnostics import StructlogDiagnosticsLog


def _capture() -> LogCapture:
    """Route structlog through an in-memory capture for one test.

    Explicitly resets the wrapper class to an unfiltered (DEBUG-level) one:
    ``structlog.configure()`` only overrides the keywords it is given, and
    another test module (or ``api/app.py``'s module-level ``create_app()``)
    may have left a level-filtering wrapper class configured that would
    otherwise silently drop ``.debug()`` calls before they ever reach this
    capture processor.
    """
    capture = LogCapture()
    structlog.configure(
        processors=[capture],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
    )
    return capture


def test_no_diagnostic_event_schema_carries_a_free_text_field() -> None:
    """The safety guarantee is structural: nothing to log means nothing can leak."""
    allowed_free_text_fields = {"message", "detail", "reason"}
    for event_type in (
        ModelCallFailed,
        SummaryGenerationFailed,
        ProposalRejected,
        RevisionConflict,
        FrontendToolingError,
    ):
        for field in dataclasses.fields(event_type):
            assert field.name in allowed_free_text_fields or field.type in (
                "str",
                "str | None",
                "bool",
                "LLMError",
            ), f"{event_type.__name__}.{field.name} sieht nach Rohdaten aus"


def test_record_always_emits_regardless_of_debug_mode() -> None:
    capture = _capture()
    adapter = StructlogDiagnosticsLog(debug_enabled=False)

    adapter.record(
        ModelCallFailed(
            task="story",
            error=LLMError(LLMErrorKind.UNAVAILABLE, "Nicht erreichbar."),
        )
    )

    assert len(capture.entries) == 1
    entry = capture.entries[0]
    assert entry["event"] == "model_call_failed"
    assert entry["task"] == "story"
    assert entry["error_message"] == "Nicht erreichbar."


def test_trace_is_silent_outside_debug_mode() -> None:
    capture = _capture()
    adapter = StructlogDiagnosticsLog(debug_enabled=False)

    adapter.trace("generate_story.call", user_prompt="Ich öffne die Tür.")

    assert capture.entries == []


def test_trace_emits_full_payload_in_debug_mode() -> None:
    capture = _capture()
    adapter = StructlogDiagnosticsLog(debug_enabled=True)

    adapter.trace("generate_story.call", user_prompt="Ich öffne die Tür.")

    assert len(capture.entries) == 1
    assert capture.entries[0]["user_prompt"] == "Ich öffne die Tür."


def test_revision_conflict_and_proposal_rejected_render_distinctly() -> None:
    capture = _capture()
    adapter = StructlogDiagnosticsLog(debug_enabled=False)

    adapter.record(RevisionConflict(detail="stale", run_id="run-1"))
    adapter.record(ProposalRejected(reason="Unbekannte Referenz"))

    events = [entry["event"] for entry in capture.entries]
    assert events == ["revision_conflict", "proposal_rejected"]


def test_frontend_tooling_error_renders_as_warning_with_its_fields() -> None:
    capture = _capture()
    adapter = StructlogDiagnosticsLog(debug_enabled=False)

    adapter.record(
        FrontendToolingError(
            source="wizard.handleCreateProposal",
            message="Failed to fetch",
            url="https://story-game.example/wizard",
            user_agent="test-agent/1.0",
        )
    )

    assert len(capture.entries) == 1
    entry = capture.entries[0]
    assert entry["event"] == "frontend_tooling_error"
    assert entry["source"] == "wizard.handleCreateProposal"
    assert entry["message"] == "Failed to fetch"
    assert entry["url"] == "https://story-game.example/wizard"
    assert entry["user_agent"] == "test-agent/1.0"
