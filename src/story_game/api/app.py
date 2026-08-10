"""FastAPI composition root for the temporary full-state test API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from story_game.api.dependencies import ApiDependencies
from story_game.application.game_state import (
    CommitCompletedTurn,
    CreateGameRun,
    GameStateOperations,
    LoadGame,
    UpdateGameConfiguration,
    PromptProfileValidator,
)
from story_game.infrastructure.llm import FilePromptPackageCatalog
from story_game.infrastructure.persistence.postgres import (
    PostgresConnectionFactory,
    PostgresGameStore,
    PostgresSchemaMigrator,
)

from .config import ApiSettings
from .errors import register_error_handlers
from .routers import router


def create_app(
    dependencies: ApiDependencies | None = None,
    settings: ApiSettings | None = None,
) -> FastAPI:
    resolved_settings = settings or ApiSettings.from_environment()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        resolved = dependencies
        if resolved is None:
            connections = PostgresConnectionFactory(resolved_settings.postgres_dsn)
            if resolved_settings.auto_migrate:
                PostgresSchemaMigrator(connections).migrate()
            store = PostgresGameStore(connections)
            resolved = ApiDependencies(
                _compose_game_state_operations(store, resolved_settings.prompt_root)
            )
        application.state.api_dependencies = resolved
        yield

    application = FastAPI(
        title=resolved_settings.title,
        version=resolved_settings.version,
        description="Temporary API for storing and loading complete story-game states.",
        lifespan=lifespan,
    )
    application.include_router(router)
    register_error_handlers(application)
    return application


def _compose_game_state_operations(
    store: PostgresGameStore, prompt_root: str
) -> GameStateOperations:
    validator = PromptProfileValidator(FilePromptPackageCatalog(prompt_root))
    return GameStateOperations(
        create=CreateGameRun(store, validator),
        load=LoadGame(store, store),
        update_configuration=UpdateGameConfiguration(store, validator),
        commit_turn=CommitCompletedTurn(store, store),
    )


app = create_app()
