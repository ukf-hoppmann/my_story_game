"""``ReportFrontendError`` (TASK-030): validate and forward a frontend report."""

from __future__ import annotations

from story_game.application.contracts import Failure, Success
from story_game.application.diagnostics import FrontendToolingError
from story_game.application.diagnostics_reporting import (
    ReportFrontendError,
    ReportFrontendErrorRejected,
    ReportFrontendErrorRequest,
)

from tests.application.diagnostics_double import FakeDiagnosticsLog


def test_apply_records_a_frontend_tooling_error_and_succeeds() -> None:
    diagnostics = FakeDiagnosticsLog()
    operation = ReportFrontendError(diagnostics)

    result = operation.apply(
        ReportFrontendErrorRequest(
            source="wizard.handleCreateProposal",
            message="Failed to fetch",
            url="https://story-game.example/wizard",
            user_agent="test-agent/1.0",
        )
    )

    assert result == Success(None)
    assert diagnostics.recorded == [
        FrontendToolingError(
            source="wizard.handleCreateProposal",
            message="Failed to fetch",
            url="https://story-game.example/wizard",
            user_agent="test-agent/1.0",
        )
    ]


def test_apply_accepts_missing_optional_fields() -> None:
    diagnostics = FakeDiagnosticsLog()
    operation = ReportFrontendError(diagnostics)

    result = operation.apply(
        ReportFrontendErrorRequest(source="auth.onTokenExpired", message="expired")
    )

    assert result == Success(None)
    assert diagnostics.recorded == [
        FrontendToolingError(source="auth.onTokenExpired", message="expired")
    ]


def test_apply_rejects_a_blank_message_without_recording() -> None:
    diagnostics = FakeDiagnosticsLog()
    operation = ReportFrontendError(diagnostics)

    result = operation.apply(ReportFrontendErrorRequest(source="wizard.handleCreateProposal", message="   "))

    assert isinstance(result, Failure)
    assert isinstance(result.error, ReportFrontendErrorRejected)
    assert diagnostics.recorded == []


def test_apply_rejects_a_blank_source_without_recording() -> None:
    diagnostics = FakeDiagnosticsLog()
    operation = ReportFrontendError(diagnostics)

    result = operation.apply(ReportFrontendErrorRequest(source="  ", message="Failed to fetch"))

    assert isinstance(result, Failure)
    assert isinstance(result.error, ReportFrontendErrorRejected)
    assert diagnostics.recorded == []
