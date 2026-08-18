"""Composition-root logging setup: two structlog profiles, stdout + file.

TASK-024 asks for two deliberately different profiles, selected by an
explicit mode switch rather than by log level alone, so a misconfigured
level can never accidentally leak raw data in production:

- ``prod`` (default): level ``INFO`` unless overridden, JSON lines.
  Only ``DiagnosticsLog.record()`` events (closed, typed, pre-redacted)
  are ever emitted.
- ``debug``: level ``DEBUG``, a colored console renderer readable in a
  terminal. In addition to ``record()`` events, this is the only profile
  in which ``DiagnosticsLog.trace()`` calls (and the LM Studio client's raw
  prompt/response logging) actually render anything.

Both profiles write to stdout *and* to a rotating file — the destination is
an orthogonal concern from which events get emitted (the mode). The active
settings come from ``configs/app.toml`` (see
``infrastructure/configuration/app_config.py``), which
``STORY_GAME_LOG_MODE``/``STORY_GAME_LOG_LEVEL`` may still override without
touching the checked-in file — see ``LoggingSettings.resolve()``.
"""

from __future__ import annotations

import dataclasses
import logging
import logging.handlers
import os
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import structlog


class LoggingMode(StrEnum):
    PROD = "prod"
    DEBUG = "debug"


@dataclass(frozen=True, slots=True)
class LoggingSettings:
    """Effective logging configuration, layered from file and environment."""

    level: str = "INFO"
    mode: LoggingMode = LoggingMode.PROD
    file_path: str | None = "logs/story-game.log"
    file_max_bytes: int = 10_485_760
    file_backup_count: int = 5

    @property
    def debug_enabled(self) -> bool:
        return self.mode is LoggingMode.DEBUG

    @classmethod
    def from_environment(cls, base: LoggingSettings | None = None) -> LoggingSettings:
        """Read ``STORY_GAME_LOG_LEVEL``/``STORY_GAME_LOG_MODE``.

        Overrides ``base`` (or the hardcoded default when no ``base`` is
        given) only where the corresponding variable is actually set —
        unset variables leave the base value untouched, so this doubles as
        the "environment overrides file" step of ``resolve()``.
        """

        defaults = base or cls()
        level = os.environ.get("STORY_GAME_LOG_LEVEL", defaults.level)
        mode_value = os.environ.get("STORY_GAME_LOG_MODE")
        if mode_value is None:
            mode = defaults.mode
        else:
            try:
                mode = LoggingMode(mode_value.strip().lower())
            except ValueError as error:
                raise ValueError(
                    f"Unbekannter STORY_GAME_LOG_MODE: {mode_value!r} "
                    f"(erwartet: {', '.join(m.value for m in LoggingMode)})"
                ) from error
        return dataclasses.replace(defaults, level=level, mode=mode)

    @classmethod
    def resolve(cls, config_path: str | Path) -> LoggingSettings:
        """Layer ``configs/app.toml`` under environment overrides.

        Precedence: ``STORY_GAME_LOG_MODE``/``STORY_GAME_LOG_LEVEL`` (if
        set) beat the checked-in file, which beats the hardcoded default.
        A missing config file is not an error — the hardcoded default
        applies, matching ``TomlAppConfigurationLoader.load_logging()``.
        """

        # Imported lazily: app_config.py imports this module for
        # ``LoggingSettings``/``LoggingMode``, so a module-level import here
        # would be circular.
        from story_game.infrastructure.configuration.app_config import (
            TomlAppConfigurationLoader,
        )

        file_settings = TomlAppConfigurationLoader().load_logging(config_path)
        return cls.from_environment(base=file_settings)


def configure_logging(settings: LoggingSettings) -> None:
    """Configure stdlib logging and structlog once, for the whole process."""

    level_name = settings.level if not settings.debug_enabled else "DEBUG"
    level = logging.getLevelNamesMapping().get(level_name.upper(), logging.INFO)

    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]
    renderer: structlog.typing.Processor = (
        structlog.dev.ConsoleRenderer()
        if settings.debug_enabled
        else structlog.processors.JSONRenderer()
    )
    formatter = structlog.stdlib.ProcessorFormatter(processor=renderer)

    handlers: list[logging.Handler] = [_stream_handler(formatter)]
    if settings.file_path:
        handlers.append(_file_handler(settings, formatter))

    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
    for handler in handlers:
        root_logger.addHandler(handler)
    root_logger.setLevel(level)

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Deliberately not cached: this process runs many tests that each
        # reconfigure structlog (e.g. via LogCapture) in the same
        # interpreter. Caching the first resolved logger would make later
        # reconfiguration silently no-op for already-obtained loggers.
        cache_logger_on_first_use=False,
    )


def _stream_handler(formatter: structlog.stdlib.ProcessorFormatter) -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    return handler


def _file_handler(
    settings: LoggingSettings, formatter: structlog.stdlib.ProcessorFormatter
) -> logging.Handler:
    assert settings.file_path is not None
    file_path = Path(settings.file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        file_path,
        maxBytes=settings.file_max_bytes,
        backupCount=settings.file_backup_count,
    )
    handler.setFormatter(formatter)
    return handler


__all__ = ["LoggingMode", "LoggingSettings", "configure_logging"]
