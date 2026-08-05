"""FastAPI composition root and lifecycle configuration."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from story_game.api.dependencies import ApiDependencies
from story_game.application.game_state import (
    CommitGameStateChanges,
    CreateInitialGameState,
    GameStateOperations,
    LoadGameState,
)
from story_game.application.ports import GameStateDocumentCodec, GameStateStore
from story_game.infrastructure.persistence.json import JsonGameStateDocumentCodec
from story_game.infrastructure.persistence.postgres import (
    PostgresConnectionFactory,
    PostgresGameStateStore,
    PostgresSchemaMigrator,
)

from .config import ApiSettings
from .errors import register_error_handlers
from .routers import router


def create_app(
    operations: GameStateOperations | None = None,
    state_codec: GameStateDocumentCodec | None = None,
    settings: ApiSettings | None = None,
) -> FastAPI:
    """Build an app with injectable operations and boundary codecs."""
    resolved_settings = settings or ApiSettings.from_environment()
    if (operations is None) != (state_codec is None):
        raise ValueError("Operationen und State-Codec müssen gemeinsam gesetzt werden")

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        if operations is None:
            connections = PostgresConnectionFactory(resolved_settings.postgres_dsn)
            if resolved_settings.auto_migrate:
                PostgresSchemaMigrator(connections).migrate()
            store = PostgresGameStateStore(connections)
            resolved = ApiDependencies(
                _compose_game_state_operations(store),
                JsonGameStateDocumentCodec(),
            )
        else:
            assert state_codec is not None
            resolved = ApiDependencies(operations, state_codec)
        application.state.api_dependencies = resolved
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


def _compose_game_state_operations(store: GameStateStore) -> GameStateOperations:
    """Wire concrete operation implementations in the composition root."""
    return GameStateOperations(
        create_initial=CreateInitialGameState(store),
        load=LoadGameState(store),
        commit=CommitGameStateChanges(store),
    )


app = create_app()
