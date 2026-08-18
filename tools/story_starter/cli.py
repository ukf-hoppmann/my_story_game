"""Argument parsing and command dispatch for the Story Game launcher."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import sys
from typing import Sequence

from .compose import (
    KNOWN_SERVICES,
    SERVICE_CHOICES,
    ComposeConfig,
    ComposeError,
    ComposeRunner,
    resolve_services,
)
from .health import backend_health, backend_port, wait_for_backend_health


@dataclass(frozen=True)
class Arguments:
    """Typed command-line values after argparse has validated them."""

    command: str
    services: tuple[str, ...] = ()
    compose_file: str | None = None
    env_file: str | None = None
    project_name: str | None = None
    follow: bool = False
    tail: str = "all"
    timestamps: bool = False
    yes: bool = False


def _service_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "services",
        nargs="*",
        choices=SERVICE_CHOICES,
        metavar="{all,backend,postgres}",
        help="Service(s), standardmäßig alle: backend, postgres",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="story-starter",
        description="Verwaltet die lokale Story-Game-Umgebung über Docker Compose.",
        epilog="Services: " + ", ".join(KNOWN_SERVICES),
    )
    parser.add_argument(
        "--compose-file",
        metavar="PATH",
        help="Alternative Docker-Compose-Datei verwenden.",
    )
    parser.add_argument(
        "--env-file",
        metavar="PATH",
        help="Docker-Compose .env-Datei verwenden.",
    )
    parser.add_argument(
        "--project-name",
        metavar="NAME",
        help="Expliziten Docker-Compose-Projektnamen verwenden.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Services starten, ohne neu zu bauen.")
    start.set_defaults(command="start")

    stop = subparsers.add_parser("stop", help="Alle Services stoppen und das Netzwerk entfernen.")
    stop.set_defaults(command="stop")

    upgrade = subparsers.add_parser("upgrade", help="Backend-Image neu bauen und alle Services starten.")
    upgrade.set_defaults(command="upgrade")

    restart = subparsers.add_parser(
        "restart", help="Alle Services oder ausgewählte Services neu starten."
    )
    _service_argument(restart)
    restart.set_defaults(command="restart")

    status = subparsers.add_parser("status", help="Status der Services anzeigen.")
    _service_argument(status)
    status.set_defaults(command="status")

    logs = subparsers.add_parser("logs", help="Logs aller oder ausgewählter Services anzeigen.")
    _service_argument(logs)
    logs.add_argument("-f", "--follow", action="store_true", help="Logs fortlaufend verfolgen.")
    logs.add_argument("--tail", metavar="N", default="all", help="Letzte N Zeilen anzeigen.")
    logs.add_argument("--timestamps", action="store_true", help="Zeitstempel ausgeben.")
    logs.set_defaults(command="logs")

    check = subparsers.add_parser(
        "check", help="Compose-Konfiguration, laufende Services und Backend prüfen."
    )
    check.set_defaults(command="check")

    clean = subparsers.add_parser(
        "clean", help="Lokale Datenbank löschen und mit leerem Schema neu starten."
    )
    clean.add_argument(
        "--yes",
        action="store_true",
        help="Datenbank-Reset ohne interaktive Sicherheitsabfrage bestätigen.",
    )
    clean.set_defaults(command="clean")
    return parser


def _arguments(namespace: argparse.Namespace) -> Arguments:
    return Arguments(
        command=namespace.command,
        services=tuple(getattr(namespace, "services", ())),
        compose_file=namespace.compose_file,
        env_file=namespace.env_file,
        project_name=namespace.project_name,
        follow=getattr(namespace, "follow", False),
        tail=getattr(namespace, "tail", "all"),
        timestamps=getattr(namespace, "timestamps", False),
        yes=getattr(namespace, "yes", False),
    )


def _start(runner: ComposeRunner, *, build: bool) -> None:
    port = backend_port()
    arguments = ["up"]
    if build:
        arguments.append("--build")
    arguments.extend(["--detach", "--wait", *KNOWN_SERVICES])
    runner.run(arguments)
    print("Story Game läuft.")
    print(f"  Backend:    http://localhost:{port}")
    print(f"  Swagger UI: http://localhost:{port}/docs")
    print(f"  OpenAPI:    http://localhost:{port}/openapi.json")
    print(f"  ReDoc:      http://localhost:{port}/redoc")


def _restart(runner: ComposeRunner, services: Sequence[str]) -> None:
    selected = resolve_services(services)
    if "backend" in selected:
        backend_port()
    runner.run(["restart", *selected])
    if "backend" in selected:
        healthy, detail = wait_for_backend_health()
        if not healthy:
            raise ComposeError(f"Backend ist nach dem Neustart nicht gesund: {detail}")
    print(f"Neu gestartet: {', '.join(selected)}")


def _status(runner: ComposeRunner, services: Sequence[str]) -> None:
    selected = resolve_services(services)
    runner.run(["ps", "--all", *selected])


def _logs(runner: ComposeRunner, arguments: Arguments) -> None:
    selected = resolve_services(arguments.services)
    command = ["logs"]
    if arguments.follow:
        command.append("--follow")
    if arguments.timestamps:
        command.append("--timestamps")
    command.extend(["--tail", arguments.tail])
    command.extend(selected)
    runner.run(command)


def _check(runner: ComposeRunner) -> int:
    runner.run(["config", "--quiet"])
    running = runner.run(["ps", "--status", "running", "--services"], capture_output=True)
    running_services = set((running.stdout or "").split())
    print("Compose-Konfiguration: OK")
    print("Laufende Services: " + (", ".join(sorted(running_services)) or "keine"))
    healthy, detail = backend_health()
    if healthy:
        print(f"Backend: OK ({detail})")
        return 0
    print(f"Backend: FEHLER ({detail})", file=sys.stderr)
    return 1


def _confirm_clean(confirmed: bool) -> None:
    if confirmed:
        return
    if not sys.stdin.isatty():
        raise ComposeError("clean benötigt in nicht-interaktiven Aufrufen die Option --yes.")
    answer = input(
        "WARNUNG: Alle lokalen Story-Game-Daten werden gelöscht. Fortfahren? [y/N] "
    )
    if answer.strip().lower() not in {"y", "yes", "j", "ja"}:
        raise ComposeError("Datenbank-Reset abgebrochen.")


def _clean(runner: ComposeRunner, *, confirmed: bool) -> None:
    backend_port()
    _confirm_clean(confirmed)
    runner.run(["down", "--volumes"])
    _start(runner, build=False)
    print("Datenbank wurde zurückgesetzt und das Schema neu initialisiert.")


def execute(arguments: Arguments) -> int:
    config = ComposeConfig.from_arguments(arguments.compose_file, arguments.env_file, arguments.project_name)
    runner = ComposeRunner(config)
    runner.ensure_available()

    if arguments.command == "start":
        _start(runner, build=False)
    elif arguments.command == "stop":
        runner.run(["down"])
        print("Story Game wurde gestoppt.")
    elif arguments.command == "upgrade":
        _start(runner, build=True)
    elif arguments.command == "restart":
        _restart(runner, arguments.services)
    elif arguments.command == "status":
        _status(runner, arguments.services)
    elif arguments.command == "logs":
        _logs(runner, arguments)
    elif arguments.command == "check":
        return _check(runner)
    elif arguments.command == "clean":
        _clean(runner, confirmed=arguments.yes)
    else:  # pragma: no cover - argparse restricts this branch
        raise ComposeError(f"Unbekannter Befehl: {arguments.command}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        parsed_arguments = list(sys.argv[1:] if argv is None else argv)
        if not parsed_arguments:
            parsed_arguments = ["start"]
        arguments = _arguments(parser.parse_args(parsed_arguments))
        return execute(arguments)
    except (ComposeError, ValueError) as error:
        print(f"Fehler: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Abgebrochen.", file=sys.stderr)
        return 130
