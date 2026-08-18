"""Shared ``DiagnosticsLog`` test double for TASK-024 coverage.

Records every ``record()`` and ``trace()`` call verbatim so a test can assert
that an operation logs the right event at the right point, without asserting
anything about how the infrastructure adapter renders it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from story_game.application.diagnostics import DiagnosticEvent


@dataclass
class FakeDiagnosticsLog:
    recorded: list[DiagnosticEvent] = field(default_factory=list)
    traced: list[tuple[str, dict[str, object]]] = field(default_factory=list)

    def record(self, event: DiagnosticEvent) -> None:
        self.recorded.append(event)

    def trace(self, step: str, **fields: object) -> None:
        self.traced.append((step, fields))
