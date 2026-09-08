from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.story_starter.cli import Arguments, build_parser, execute, main
from tools.story_starter.compose import (
    ComposeConfig,
    ComposeError,
    ComposeRunner,
    resolve_services,
)


def test_logs_help_lists_all_supported_services(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        build_parser().parse_args(["logs", "-h"])

    assert error.value.code == 0
    assert "{all,backend,postgres,frontend}" in capsys.readouterr().out


def test_resolve_services_defaults_to_all_and_rejects_mixed_all() -> None:
    assert resolve_services(()) == ("backend", "postgres", "frontend", "nginx", "keycloak")
    assert resolve_services(("postgres",)) == ("postgres",)

    with pytest.raises(ComposeError, match="all"):
        resolve_services(("all", "backend"))


def test_start_runs_the_stack_without_building() -> None:
    fake_runner = _FakeRunner()

    with patch("tools.story_starter.cli.ComposeRunner", return_value=fake_runner):
        assert execute(Arguments("start")) == 0

    assert fake_runner.commands == [["up", "--detach", "--wait", "backend", "postgres", "frontend", "nginx", "keycloak"]]


def test_upgrade_adds_build_flag() -> None:
    fake_runner = _FakeRunner()

    with patch("tools.story_starter.cli.ComposeRunner", return_value=fake_runner):
        assert execute(Arguments("upgrade")) == 0

    assert fake_runner.commands == [["up", "--build", "--detach", "--wait", "backend", "postgres", "frontend", "nginx", "keycloak"]]


def test_restart_defaults_to_all_but_accepts_one_service() -> None:
    fake_runner = _FakeRunner()

    with patch("tools.story_starter.cli.ComposeRunner", return_value=fake_runner), patch(
        "tools.story_starter.cli.wait_for_backend_health",
        return_value=(True, "http://localhost:8000/health"),
    ):
        assert execute(Arguments("restart")) == 0
        assert execute(Arguments("restart", services=("backend",))) == 0

    assert fake_runner.commands == [
        ["restart", "backend", "postgres", "frontend", "nginx", "keycloak"],
        ["restart", "backend"],
    ]


def test_clean_requires_confirmation_before_removing_the_volume() -> None:
    fake_runner = _FakeRunner()

    with patch("tools.story_starter.cli.ComposeRunner", return_value=fake_runner), patch(
        "tools.story_starter.cli.sys.stdin.isatty", return_value=True
    ), patch("builtins.input", return_value="n"):
        with pytest.raises(ComposeError, match="abgebrochen"):
            execute(Arguments("clean"))

    assert fake_runner.commands == []


def test_no_arguments_remains_an_alias_for_start() -> None:
    with patch("tools.story_starter.cli.execute", return_value=0) as execute_mock:
        assert main([]) == 0

    assert execute_mock.call_args.args[0].command == "start"


def test_down_removes_containers_and_volumes() -> None:
    fake_runner = _FakeRunner()

    with patch("tools.story_starter.cli.ComposeRunner", return_value=fake_runner):
        assert execute(Arguments("down")) == 0

    assert fake_runner.commands == [["down", "--volumes", "--remove-orphans"]]


def test_confirmed_clean_removes_volumes_then_starts_without_build() -> None:
    fake_runner = _FakeRunner()

    with patch("tools.story_starter.cli.ComposeRunner", return_value=fake_runner):
        assert execute(Arguments("clean", yes=True)) == 0

    assert fake_runner.commands == [
        ["down", "--volumes"],
        ["up", "--detach", "--wait", "backend", "postgres", "frontend", "nginx", "keycloak"],
    ]


def test_execute_loads_the_resolved_env_file_into_the_process_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / "docker.env"
    env_file.write_text("FRONTEND_HOST_PORT=5172\n")
    monkeypatch.delenv("FRONTEND_HOST_PORT", raising=False)
    fake_runner = _FakeRunner()
    fake_config = ComposeConfig(
        repository_root=tmp_path, compose_file=tmp_path / "compose.yaml", env_file=env_file
    )

    with patch(
        "tools.story_starter.cli.ComposeConfig.from_arguments", return_value=fake_config
    ), patch("tools.story_starter.cli.ComposeRunner", return_value=fake_runner):
        assert execute(Arguments("start")) == 0

    assert os.environ["FRONTEND_HOST_PORT"] == "5172"


def test_execute_does_not_override_an_already_exported_variable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / "docker.env"
    env_file.write_text("FRONTEND_HOST_PORT=5172\n")
    monkeypatch.setenv("FRONTEND_HOST_PORT", "9999")
    fake_runner = _FakeRunner()
    fake_config = ComposeConfig(
        repository_root=tmp_path, compose_file=tmp_path / "compose.yaml", env_file=env_file
    )

    with patch(
        "tools.story_starter.cli.ComposeConfig.from_arguments", return_value=fake_config
    ), patch("tools.story_starter.cli.ComposeRunner", return_value=fake_runner):
        assert execute(Arguments("start")) == 0

    assert os.environ["FRONTEND_HOST_PORT"] == "9999"


class _FakeRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def ensure_available(self) -> None:
        return None

    def run(self, arguments: list[str], *, capture_output: bool = False):
        self.commands.append(arguments)
        return type("Completed", (), {"stdout": "backend\npostgres\nfrontend\n", "stderr": ""})()
