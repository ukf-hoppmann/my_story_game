"""Accept a frontend-reported tooling error and forward it to diagnostics.

TASK-030: everything that never reached the backend as a typed API error
(network failure, JSON-parse failure, a synchronous JS exception thrown
before a request) is reported by the frontend itself via
``POST /api/v1/diagnostics/frontend-errors``. This is the single application
operation that endpoint calls — it is deliberately the only place a router
reaches ``DiagnosticsLog.record()`` for this event, keeping the transport
adapter thin per the ports/operation-contract rules.
"""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.diagnostics import DiagnosticsLog, FrontendToolingError


@dataclass(frozen=True, slots=True)
class ReportFrontendErrorRequest:
    source: str
    message: str
    url: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True, slots=True)
class ReportFrontendErrorRejected:
    """The report failed basic validation and was dropped without logging.

    The API schema already enforces field-length limits before this ever
    runs; this is defense-in-depth against a blank ``source``/``message``
    slipping through, not the primary line of validation.
    """

    detail: str


class ReportFrontendError:
    def __init__(self, diagnostics: DiagnosticsLog) -> None:
        self._diagnostics = diagnostics

    def apply(
        self, request: ReportFrontendErrorRequest
    ) -> OperationResult[None, ReportFrontendErrorRejected]:
        if not request.source.strip():
            return Failure(ReportFrontendErrorRejected("source darf nicht leer sein"))
        if not request.message.strip():
            return Failure(ReportFrontendErrorRejected("message darf nicht leer sein"))
        self._diagnostics.record(
            FrontendToolingError(
                source=request.source,
                message=request.message,
                url=request.url,
                user_agent=request.user_agent,
            )
        )
        return Success(None)


__all__ = [
    "ReportFrontendError",
    "ReportFrontendErrorRejected",
    "ReportFrontendErrorRequest",
]
