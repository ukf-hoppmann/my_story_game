"""Small, shell-free adapter around Docker Compose."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
from typing import Sequence


KNOWN_SERVICES = ("backend", "postgres", "frontend")
SERVICE_CHOICES = ("all", *KNOWN_SERVICES)


class ComposeError(RuntimeError):
    """Raised when Docker Compose cannot be invoked successfully."""


@dataclass(frozen=True)
class ComposeConfig:
    """Resolved paths and optional Compose project settings."""

    repository_root: Path
    compose_file: Path
    env_file: Path | None = None
    project_name: str | None = None

    @classmethod
    def from_arguments(
        cls, compose_file: str | None, env_file: str | None, project_name: str | None
    ) -> "ComposeConfig":
        repository_root = Path(__file__).resolve().parents[2]
        resolved_compose_file = Path(compose_file or repository_root / "compose.yaml")
        if not resolved_compose_file.is_absolute():
            resolved_compose_file = (Path.cwd() / resolved_compose_file).resolve()
        else:
            resolved_compose_file = resolved_compose_file.resolve()

        resolved_env_file = None
        if env_file:
            resolved_env_file = Path(env_file)
            if not resolved_env_file.is_absolute():
                resolved_env_file = (Path.cwd() / resolved_env_file).resolve()
            else:
                resolved_env_file = resolved_env_file.resolve()

        return cls(repository_root, resolved_compose_file, resolved_env_file, project_name)


def resolve_services(services: Sequence[str]) -> tuple[str, ...]:
    """Resolve optional service arguments, defaulting to the complete stack."""

    selected = tuple(services)
    if not selected or "all" in selected:
        if selected and selected != ("all",):
            raise ComposeError("'all' darf nicht mit einem einzelnen Service kombiniert werden.")
        return KNOWN_SERVICES
    return selected


class ComposeRunner:
    """Execute Docker Compose with explicit argument arrays and repository cwd."""

    def __init__(self, config: ComposeConfig) -> None:
        self.config = config

    def _command(self, arguments: Sequence[str]) -> list[str]:
        command = ["docker", "compose"]
        if self.config.env_file:
            command.extend(["--env-file", str(self.config.env_file)])
        if self.config.project_name:
            command.extend(["--project-name", self.config.project_name])
        command.extend(["--file", str(self.config.compose_file)])
        command.extend(arguments)
        return command

    def run(
        self,
        arguments: Sequence[str],
        *,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        if not self.config.compose_file.is_file():
            raise ComposeError(f"Compose-Datei fehlt: {self.config.compose_file}")
        try:
            result = subprocess.run(
                self._command(arguments),
                cwd=self.config.repository_root,
                env=os.environ.copy(),
                check=False,
                text=True,
                capture_output=capture_output,
            )
        except FileNotFoundError as error:
            raise ComposeError("Docker wurde nicht gefunden.") from error
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            suffix = f": {detail}" if detail else ""
            raise ComposeError(
                f"Docker Compose fehlgeschlagen (Exit-Code {result.returncode}){suffix}"
            )
        return result

    def ensure_available(self) -> None:
        """Fail early with a focused message when Docker Compose is unavailable."""

        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                cwd=self.config.repository_root,
                env=os.environ.copy(),
                check=False,
                text=True,
                capture_output=True,
            )
        except FileNotFoundError as error:
            raise ComposeError("Docker wurde nicht gefunden.") from error
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            suffix = f": {detail}" if detail else ""
            raise ComposeError(f"Docker Compose ist nicht verfügbar{suffix}")
