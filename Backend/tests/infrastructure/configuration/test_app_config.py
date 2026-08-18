from __future__ import annotations

from pathlib import Path

import pytest

from story_game.infrastructure.configuration.app_config import (
    AppConfigurationError,
    TomlAppConfigurationLoader,
)
from story_game.infrastructure.logging_config import LoggingMode, LoggingSettings


def write_config(tmp_path: Path, document: str) -> Path:
    path = tmp_path / "app.toml"
    path.write_text(document, encoding="utf-8")
    return path


def test_a_missing_file_yields_the_hardcoded_defaults(tmp_path: Path) -> None:
    settings = TomlAppConfigurationLoader().load_logging(tmp_path / "does-not-exist.toml")

    assert settings == LoggingSettings()


def test_a_valid_file_is_parsed_completely(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        """
        [logging]
        mode = "debug"
        level = "WARNING"
        file_path = "logs/custom.log"
        file_max_bytes = 2048
        file_backup_count = 2
        """,
    )

    settings = TomlAppConfigurationLoader().load_logging(path)

    assert settings == LoggingSettings(
        level="WARNING",
        mode=LoggingMode.DEBUG,
        file_path="logs/custom.log",
        file_max_bytes=2048,
        file_backup_count=2,
    )


def test_an_empty_logging_table_yields_defaults(tmp_path: Path) -> None:
    path = write_config(tmp_path, "[logging]\n")

    settings = TomlAppConfigurationLoader().load_logging(path)

    assert settings == LoggingSettings()


def test_an_unknown_top_level_key_is_rejected(tmp_path: Path) -> None:
    path = write_config(tmp_path, "[unknown]\nfoo = 1\n")

    with pytest.raises(AppConfigurationError, match="Unbekannte Felder"):
        TomlAppConfigurationLoader().load_logging(path)


def test_an_unknown_logging_key_is_rejected(tmp_path: Path) -> None:
    path = write_config(tmp_path, "[logging]\nfoo = 1\n")

    with pytest.raises(AppConfigurationError, match="Unbekannte Felder"):
        TomlAppConfigurationLoader().load_logging(path)


def test_an_unknown_mode_is_rejected(tmp_path: Path) -> None:
    path = write_config(tmp_path, '[logging]\nmode = "verbose"\n')

    with pytest.raises(AppConfigurationError, match="logging.mode"):
        TomlAppConfigurationLoader().load_logging(path)


def test_an_unknown_level_is_rejected(tmp_path: Path) -> None:
    path = write_config(tmp_path, '[logging]\nlevel = "SUPER_LOUD"\n')

    with pytest.raises(AppConfigurationError, match="logging.level"):
        TomlAppConfigurationLoader().load_logging(path)


@pytest.mark.parametrize("value", [0, -1, 1.5, "big"])
def test_a_non_positive_file_max_bytes_is_rejected(tmp_path: Path, value: object) -> None:
    path = write_config(tmp_path, f"[logging]\nfile_max_bytes = {value!r}\n")

    with pytest.raises(AppConfigurationError, match="file_max_bytes"):
        TomlAppConfigurationLoader().load_logging(path)


def test_invalid_toml_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "app.toml"
    path.write_text("not valid toml [[[", encoding="utf-8")

    with pytest.raises(AppConfigurationError, match="kein gültiges TOML"):
        TomlAppConfigurationLoader().load_logging(path)
