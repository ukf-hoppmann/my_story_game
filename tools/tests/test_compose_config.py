from __future__ import annotations

from pathlib import Path

import pytest

from tools.story_starter import compose as compose_module
from tools.story_starter.compose import ComposeConfig, DEFAULT_ENV_FILE, parse_env_file


def test_default_env_file_is_the_project_owned_docker_env() -> None:
    """Without --env-file, the project's own configs/docker/docker.env is used.

    Docker Compose does not auto-load this file (only a plain ``.env`` next
    to the compose file would be), so without this default a caller's edits
    to ``configs/docker/docker.env`` (e.g. moving the frontend off a port
    already used by another project) silently never reach the containers.
    """
    config = ComposeConfig.from_arguments(None, None, None)

    assert config.env_file == config.repository_root / DEFAULT_ENV_FILE
    assert config.env_file.is_file()


def test_explicit_env_file_overrides_the_default() -> None:
    config = ComposeConfig.from_arguments(None, "configs/docker/docker.env", None)

    assert config.env_file == config.repository_root / DEFAULT_ENV_FILE


def test_missing_default_env_file_leaves_env_file_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A checkout without configs/docker/docker.env (e.g. a stripped-down
    # one) must not make Compose invocation fail — it should behave exactly
    # like today: no --env-file at all.
    monkeypatch.setattr(
        compose_module, "DEFAULT_ENV_FILE", Path("configs/docker/does-not-exist.env")
    )

    config = ComposeConfig.from_arguments(None, None, None)

    assert config.env_file is None


def test_parse_env_file_ignores_blank_lines_and_comments(tmp_path: Path) -> None:
    env_file = tmp_path / "docker.env"
    env_file.write_text(
        "# comment\n"
        "\n"
        "FRONTEND_HOST_PORT=5172\n"
        "  BACKEND_HOST_PORT = 8000  \n"
        "not-a-valid-line\n"
    )

    assert parse_env_file(env_file) == {
        "FRONTEND_HOST_PORT": "5172",
        "BACKEND_HOST_PORT": "8000",
    }
