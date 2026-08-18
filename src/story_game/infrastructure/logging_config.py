"""Composition-root logging setup: two structlog profiles, one stdout stream.

TASK-024 asks for two deliberately different profiles, selected by an
explicit mode switch rather than by log level alone, so a misconfigured
level can never accidentally leak raw data in production:

- ``prod`` (default): level ``INFO`` unless overridden, JSON lines on
  stdout, machine-parseable. Only ``DiagnosticsLog.record()`` events
  (closed, typed, pre-redacted) are ever emitted.
- ``debug``: level ``DEBUG``, a colored console renderer readable in a
  terminal. In addition to ``record()`` events, this is the only profile
  in which ``DiagnosticsLog.trace()`` calls (and the LM Studio client's raw
  prompt/response logging) actually render anything.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from enum import StrEnum

import structlog


class LoggingMode(StrEnum):
    PROD = "prod"
    DEBUG = "debug"


@dataclass(frozen=True, slots=True)
class LoggingSettings:
    """Runtime-only logging configuration, read from the environment."""

    level: str = "INFO"
    mode: LoggingMode = LoggingMode.PROD

    @property
    def debug_enabled(self) -> bool:
        return self.mode is LoggingMode.DEBUG

    @classmethod
    def from_environment(cls) -> LoggingSettings:
        """Read ``STORY_GAME_LOG_LEVEL``/``STORY_GAME_LOG_MODE``, defaulting to prod."""

        level = os.environ.get("STORY_GAME_LOG_LEVEL", "INFO")
        mode_value = os.environ.get("STORY_GAME_LOG_MODE", LoggingMode.PROD.value)
        try:
            mode = LoggingMode(mode_value.strip().lower())
        except ValueError as error:
            raise ValueError(
                f"Unbekannter STORY_GAME_LOG_MODE: {mode_value!r} "
                f"(erwartet: {', '.join(m.value for m in LoggingMode)})"
            ) from error
        return cls(level=level, mode=mode)


def configure_logging(settings: LoggingSettings) -> None:
    """Configure stdlib logging and structlog once, for the whole process."""

    level_name = settings.level if not settings.debug_enabled else "DEBUG"
    level = logging.getLevelNamesMapping().get(level_name.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    renderer: structlog.typing.Processor = (
        structlog.dev.ConsoleRenderer()
        if settings.debug_enabled
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        # Deliberately not cached: this process runs many tests that each
        # reconfigure structlog (e.g. via LogCapture) in the same
        # interpreter. Caching the first resolved logger would make later
        # reconfiguration silently no-op for already-obtained loggers.
        cache_logger_on_first_use=False,
    )


__all__ = ["LoggingMode", "LoggingSettings", "configure_logging"]
