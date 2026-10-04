"""Validated TOML configuration for the central, versioned application settings.

Mirrors ``llm.py``'s ``TomlLlmConfigurationLoader`` style (unknown-key
rejection, explicit type/range validation, wraps parse errors into one
project-specific error type). Currently three sections: ``[logging]``,
``[story_summary]`` and ``[scene_image]``. A missing file, or a missing section within it, is not
an error — callers get the hardcoded settings defaults, so tests and ad-hoc
runs work without it.
"""

from __future__ import annotations

import logging
import math
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from story_game.infrastructure.logging_config import LoggingMode, LoggingSettings

if TYPE_CHECKING:
    from .scene_image import SceneImageSettings


class AppConfigurationError(ValueError):
    """``configs/app.toml`` cannot safely describe the application settings."""


@dataclass(frozen=True, slots=True)
class StorySummarySettings:
    """How the summary-segment chain (TASK-032) is tuned.

    ``interval`` and ``context_segment_count`` are deliberately independent:
    ``interval`` governs how often the rare, batched summarization call runs
    (every N turns); ``context_segment_count`` governs how many of the
    resulting segments the cheap, per-turn narration context carries.
    Changing one must never silently change the cost of the other.
    """

    interval: int = 4
    context_segment_count: int = 3

    def __post_init__(self) -> None:
        if self.interval < 1:
            raise ValueError("interval muss mindestens 1 sein")
        if self.context_segment_count < 0:
            raise ValueError("context_segment_count darf nicht negativ sein")


class TomlAppConfigurationLoader:
    """Load and validate the one project-owned ``configs/app.toml`` file."""

    def load_logging(self, path: str | Path) -> LoggingSettings:
        table = self._section(path, "logging")
        return self._logging(table, Path(path))

    def load_story_summary(self, path: str | Path) -> StorySummarySettings:
        table = self._section(path, "story_summary")
        return self._story_summary(table, Path(path))

    def load_scene_image(self, path: str | Path) -> "SceneImageSettings":
        from .scene_image import parse_scene_image

        table = self._section(path, "scene_image")
        return parse_scene_image(table, Path(path))

    def _section(self, path: str | Path, name: str) -> dict[str, Any]:
        config_path = Path(path)
        if not config_path.exists():
            return {}
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
        _keys(document, {"logging", "story_summary", "scene_image"}, "die Hauptkonfiguration", config_path)
        table = document.get(name, {})
        return _table(table, name, config_path)

    def _story_summary(
        self, table: dict[str, Any], path: Path
    ) -> StorySummarySettings:
        defaults = StorySummarySettings()
        _keys(table, {"interval", "context_segment_count"}, "story_summary", path)
        interval = _positive_int(
            table.get("interval", defaults.interval), "story_summary.interval", path
        )
        context_segment_count = table.get(
            "context_segment_count", defaults.context_segment_count
        )
        if isinstance(context_segment_count, bool) or not isinstance(
            context_segment_count, int
        ):
            raise AppConfigurationError(
                f"{path}: story_summary.context_segment_count muss eine ganze Zahl sein"
            )
        if context_segment_count < 0:
            raise AppConfigurationError(
                f"{path}: story_summary.context_segment_count darf nicht negativ sein"
            )
        return StorySummarySettings(
            interval=interval, context_segment_count=context_segment_count
        )

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
