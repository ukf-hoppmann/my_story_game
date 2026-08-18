"""Validated TOML configuration for the central, versioned application settings.

Mirrors ``llm.py``'s ``TomlLlmConfigurationLoader`` style (unknown-key
rejection, explicit type/range validation, wraps parse errors into one
project-specific error type) for the one section that exists so far:
``[logging]``. A missing file is not an error — callers get the hardcoded
``LoggingSettings`` defaults, so tests and ad-hoc runs work without it.
"""

from __future__ import annotations

import logging
import math
import tomllib
from pathlib import Path
from typing import Any

from story_game.infrastructure.logging_config import LoggingMode, LoggingSettings


class AppConfigurationError(ValueError):
    """``configs/app.toml`` cannot safely describe the application settings."""


class TomlAppConfigurationLoader:
    """Load and validate the one project-owned ``configs/app.toml`` file."""

    def load_logging(self, path: str | Path) -> LoggingSettings:
        config_path = Path(path)
        if not config_path.exists():
            return LoggingSettings()
        try:
            document = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except OSError as error:
            raise AppConfigurationError(
                f"Die Anwendungskonfiguration konnte nicht gelesen werden: {config_path}"
            ) from error
        except tomllib.TOMLDecodeError as error:
            raise AppConfigurationError(
                f"Die Anwendungskonfiguration ist kein gültiges TOML: {config_path}"
            ) from error
        _keys(document, {"logging"}, "die Hauptkonfiguration", config_path)
        table = document.get("logging", {})
        return self._logging(_table(table, "logging", config_path), config_path)

    def _logging(self, table: dict[str, Any], path: Path) -> LoggingSettings:
        defaults = LoggingSettings()
        _keys(
            table,
            {"mode", "level", "file_path", "file_max_bytes", "file_backup_count"},
            "logging",
            path,
        )

        mode_value = table.get("mode", defaults.mode.value)
        if not isinstance(mode_value, str):
            raise AppConfigurationError(f"{path}: logging.mode muss Text sein")
        try:
            mode = LoggingMode(mode_value.strip().lower())
        except ValueError as error:
            raise AppConfigurationError(
                f"{path}: logging.mode ist unbekannt: {mode_value!r} "
                f"(erwartet: {', '.join(m.value for m in LoggingMode)})"
            ) from error

        level = table.get("level", defaults.level)
        if not isinstance(level, str) or not level.strip():
            raise AppConfigurationError(f"{path}: logging.level muss nichtleerer Text sein")
        level = level.strip()
        if level.upper() not in logging.getLevelNamesMapping():
            raise AppConfigurationError(f"{path}: logging.level ist unbekannt: {level!r}")

        file_path = table.get("file_path", defaults.file_path)
        if file_path is not None and (
            not isinstance(file_path, str) or not file_path.strip()
        ):
            raise AppConfigurationError(
                f"{path}: logging.file_path muss nichtleerer Text oder unbelegt sein"
            )

        file_max_bytes = _positive_int(
            table.get("file_max_bytes", defaults.file_max_bytes),
            "logging.file_max_bytes",
            path,
        )
        file_backup_count = _positive_int(
            table.get("file_backup_count", defaults.file_backup_count),
            "logging.file_backup_count",
            path,
        )

        return LoggingSettings(
            level=level,
            mode=mode,
            file_path=file_path,
            file_max_bytes=file_max_bytes,
            file_backup_count=file_backup_count,
        )


def _table(value: Any, key: str, path: Path) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AppConfigurationError(f"{path}: {key} muss eine Tabelle sein")
    return value


def _keys(document: dict[str, Any], allowed: set[str], label: str, path: Path) -> None:
    unknown = set(document) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise AppConfigurationError(f"{path}: Unbekannte Felder in {label}: {names}")


def _positive_int(value: Any, label: str, path: Path) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AppConfigurationError(f"{path}: {label} muss eine positive ganze Zahl sein")
    if not math.isfinite(value) or value <= 0:
        raise AppConfigurationError(f"{path}: {label} muss eine positive ganze Zahl sein")
    return value


__all__ = ["AppConfigurationError", "TomlAppConfigurationLoader"]
