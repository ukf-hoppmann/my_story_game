from __future__ import annotations

import logging.handlers
from pathlib import Path

import pytest
import structlog

from story_game.infrastructure.logging_config import (
    LoggingMode,
    LoggingSettings,
    configure_logging,
)


def write_config(tmp_path: Path, document: str) -> Path:
    path = tmp_path / "app.toml"
    path.write_text(document, encoding="utf-8")
    return path


def test_resolve_uses_the_file_when_no_environment_variable_is_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("STORY_GAME_LOG_MODE", raising=False)
    monkeypatch.delenv("STORY_GAME_LOG_LEVEL", raising=False)
    path = write_config(tmp_path, '[logging]\nmode = "debug"\n')

    settings = LoggingSettings.resolve(path)

    assert settings.mode is LoggingMode.DEBUG


def test_resolve_lets_the_environment_variable_override_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STORY_GAME_LOG_MODE", "prod")
    monkeypatch.delenv("STORY_GAME_LOG_LEVEL", raising=False)
    path = write_config(tmp_path, '[logging]\nmode = "debug"\n')

    settings = LoggingSettings.resolve(path)

    assert settings.mode is LoggingMode.PROD


def test_resolve_falls_back_to_defaults_without_a_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("STORY_GAME_LOG_MODE", raising=False)
    monkeypatch.delenv("STORY_GAME_LOG_LEVEL", raising=False)

    settings = LoggingSettings.resolve(tmp_path / "does-not-exist.toml")

    assert settings == LoggingSettings()


def test_configure_logging_writes_the_same_events_to_stdout_and_the_file(
    tmp_path: Path,
) -> None:
    log_file = tmp_path / "story-game.log"
    configure_logging(
        LoggingSettings(mode=LoggingMode.DEBUG, file_path=str(log_file))
    )

    structlog.get_logger("story_game.diagnostics").warning(
        "test_event", detail="hello"
    )
    for handler in logging.getLogger().handlers:
        handler.flush()

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "test_event" in content
    assert "hello" in content


def test_configure_logging_rotates_the_file(tmp_path: Path) -> None:
    log_file = tmp_path / "story-game.log"
    configure_logging(
        LoggingSettings(
            mode=LoggingMode.DEBUG,
            file_path=str(log_file),
            file_max_bytes=1,
            file_backup_count=2,
        )
    )

    for _ in range(20):
        structlog.get_logger("story_game.diagnostics").warning(
            "test_event", detail="hello world, this is a long enough line"
        )
    for handler in logging.getLogger().handlers:
        handler.flush()

    rotated = list(tmp_path.glob("story-game.log.*"))
    assert rotated, "expected at least one rotated backup file"
