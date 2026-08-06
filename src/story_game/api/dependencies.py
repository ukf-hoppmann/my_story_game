"""FastAPI dependencies exposing application contracts, not infrastructure."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from story_game.application.game_state import GameStateOperations


@dataclass(frozen=True, slots=True)
class ApiDependencies:
    """Application-facing dependencies required by the HTTP adapter."""

    operations: GameStateOperations


def get_api_dependencies(request: Request) -> ApiDependencies:
    """Resolve the application contracts installed by the app lifespan."""
    dependencies = getattr(request.app.state, "api_dependencies", None)
    if not isinstance(dependencies, ApiDependencies):
        raise RuntimeError("Die API-Abhängigkeiten wurden nicht initialisiert")
    return dependencies
