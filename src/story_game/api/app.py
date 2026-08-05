"""FastAPI composition root and lifecycle configuration."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from story_game.application.game_state_service import GameStateService
from story_game.infrastructure.persistence.postgres import (
    PostgresConnectionFactory,
    PostgresGameStateStore,
    PostgresSchemaMigrator,
)

from .config import ApiSettings
from .errors import register_error_handlers
from .routers import router


def create_app(
    service: GameStateService | None = None,
    settings: ApiSettings | None = None,
) -> FastAPI:
    """Build an app with injectable application services for isolated tests."""
    resolved_settings = settings or ApiSettings.from_environment()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        if service is None:
            connections = PostgresConnectionFactory(resolved_settings.postgres_dsn)
            if resolved_settings.auto_migrate:
                PostgresSchemaMigrator(connections).migrate()
            store = PostgresGameStateStore(connections)
            application.state.game_state_service = GameStateService(store, store)
        else:
            application.state.game_state_service = service
        yield

    application = FastAPI(
        title=resolved_settings.title,
        version=resolved_settings.version,
        description=(
            "Application-controlled story-game state API. "
            "Only approved change sets can advance the canonical state."
        ),
        lifespan=lifespan,
    )
    application.include_router(router)
    register_error_handlers(application)
    return application


app = create_app()
