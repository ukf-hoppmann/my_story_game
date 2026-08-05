"""FastAPI dependencies exposing application services, not database objects."""

from __future__ import annotations

from fastapi import Request

from story_game.application.game_state_service import GameStateService


def get_game_state_service(request: Request) -> GameStateService:
    """Resolve the service installed by the application lifespan."""
    service = getattr(request.app.state, "game_state_service", None)
    if not isinstance(service, GameStateService):
        raise RuntimeError("Der GameStateService wurde nicht initialisiert")
    return service
