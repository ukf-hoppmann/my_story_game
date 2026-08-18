"""FastAPI dependencies exposing application contracts, not infrastructure."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from story_game.application import InitializeGameRun, PlayStoryTurn, StartPlaythrough, RunInitiator
from story_game.application.game_state import GameStateOperations

from .config import ApiSettings


@dataclass(frozen=True, slots=True)
class ApiDependencies:
    """Application-facing dependencies required by the HTTP adapter."""

    operations: GameStateOperations
    initialize_run: InitializeGameRun
    play_turn: PlayStoryTurn
    start_playthrough: StartPlaythrough


def get_api_dependencies(request: Request) -> ApiDependencies:
    """Resolve the application contracts installed by the app lifespan."""
    dependencies = getattr(request.app.state, "api_dependencies", None)
    if not isinstance(dependencies, ApiDependencies):
        raise RuntimeError("Die API-Abhängigkeiten wurden nicht initialisiert")
    return dependencies


def get_current_initiator(request: Request) -> RunInitiator:
    """Fixed development identity until Keycloak token parsing lands.

    Every request currently resolves to the same identity. Swapping this for
    real token parsing later changes only this function's body — no router,
    schema, or application code needs to change.
    """
    settings = getattr(request.app.state, "api_settings", None)
    if not isinstance(settings, ApiSettings):
        raise RuntimeError("Die API-Einstellungen wurden nicht initialisiert")
    return RunInitiator(settings.dev_issuer, settings.dev_subject)
