"""FastAPI composition root for the story-game run/turn API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from story_game.api.dependencies import ApiDependencies
from story_game.application import (
    ConfirmGameRunProposal,
    ExtractInitialWorldState,
    ExtractStoryTurnChanges,
    GenerateStory,
    InitializeStory,
    PlayStoryTurn,
    ProposeGameRun,
    StartPlaythrough,
    SummarizeStory,
)
from story_game.application.approve_story_turn_changes import ApproveStoryTurnChanges
from story_game.application.game_state import (
    CommitCompletedTurn,
    CreateGameRun,
    GameStateOperations,
    ListPlayableRuns,
    LoadGame,
    UpdateGameConfiguration,
    PromptProfileValidator,
)
from story_game.application.llm import (
    ExtractionPromptSelectionResolver,
    InitialExtractionPromptSelectionResolver,
    StoryInitializationPromptResolver,
    StoryPromptSelectionResolver,
    SummaryPromptSelectionResolver,
)
from story_game.application.story_initialization import GenerateInitialStoryState
from story_game.application.story_turn_context import build_story_turn_context_selection
from story_game.infrastructure.configuration import (
    TomlGenerationConfigurationResolver,
    TomlLlmConfigurationLoader,
)
from story_game.infrastructure.diagnostics import StructlogDiagnosticsLog
from story_game.infrastructure.llm import FilePromptPackageCatalog
from story_game.infrastructure.llm.lmstudio import (
    LmStudioClient,
    LmStudioInitialWorldExtractionAdapter,
    LmStudioSettings,
    LmStudioStoryGenerationAdapter,
    LmStudioStoryInitializationAdapter,
    LmStudioStorySummaryAdapter,
    LmStudioTurnExtractionAdapter,
)
from story_game.infrastructure.logging_config import LoggingSettings, configure_logging
from story_game.infrastructure.persistence.in_memory_proposal_store import (
    InMemoryProposalStore,
)
from story_game.infrastructure.persistence.postgres import (
    PostgresConnectionFactory,
    PostgresGameStore,
    PostgresSchemaMigrator,
)

from .config import ApiSettings
from .default_configuration import DEFAULT_GAME_CONFIGURATION
from .errors import register_error_handlers
from .routers import router

__all__ = ["DEFAULT_GAME_CONFIGURATION", "create_app", "app"]


def create_app(
    dependencies: ApiDependencies | None = None,
    settings: ApiSettings | None = None,
    logging_settings: LoggingSettings | None = None,
) -> FastAPI:
    resolved_settings = settings or ApiSettings.from_environment()
    resolved_logging_settings = logging_settings or LoggingSettings.resolve(
        resolved_settings.config_path
    )
    configure_logging(resolved_logging_settings)
    diagnostics = StructlogDiagnosticsLog(
        debug_enabled=resolved_logging_settings.debug_enabled
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        resolved = dependencies
        llm_client: LmStudioClient | None = None
        if resolved is None:
            connections = PostgresConnectionFactory(resolved_settings.postgres_dsn)
            if resolved_settings.auto_migrate:
                PostgresSchemaMigrator(connections).migrate()
            store = PostgresGameStore(connections)
            proposal_store = InMemoryProposalStore()
            llm_client = _build_llm_client(resolved_settings)
            resolved = ApiDependencies(
                operations=_compose_game_state_operations(
                    store, resolved_settings.prompt_root, diagnostics
                ),
                propose_run=_compose_propose_game_run(
                    proposal_store, resolved_settings, llm_client, diagnostics
                ),
                confirm_proposal=_compose_confirm_game_run_proposal(
                    store, proposal_store, resolved_settings, diagnostics
                ),
                play_turn=_compose_play_story_turn(
                    store, resolved_settings, llm_client, diagnostics
                ),
                start_playthrough=_compose_start_playthrough(
                    store, resolved_settings, diagnostics
                ),
            )
        application.state.api_dependencies = resolved
        application.state.api_settings = resolved_settings
        try:
            yield
        finally:
            if llm_client is not None:
                llm_client.close()

    application = FastAPI(
        title=resolved_settings.title,
        version=resolved_settings.version,
        description="API for creating, listing, and playing story-game runs.",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(router)
    register_error_handlers(application)
    return application


def _compose_game_state_operations(
    store: PostgresGameStore,
    prompt_root: str,
    diagnostics: StructlogDiagnosticsLog,
) -> GameStateOperations:
    validator = PromptProfileValidator(FilePromptPackageCatalog(prompt_root))
    return GameStateOperations(
        create=CreateGameRun(store, validator),
        load=LoadGame(store, store),
        update_configuration=UpdateGameConfiguration(store, validator),
        commit_turn=CommitCompletedTurn(store, store, diagnostics),
        list_playable_runs=ListPlayableRuns(store),
    )


def _build_llm_client(settings: ApiSettings) -> LmStudioClient:
    runtime_configuration = TomlLlmConfigurationLoader().load(settings.llm_config_path)
    provider = runtime_configuration.provider("lmstudio")
    return LmStudioClient(
        LmStudioSettings(provider.base_url, timeout_seconds=provider.timeout_seconds)
    )


def _compose_propose_game_run(
    proposal_store: InMemoryProposalStore,
    settings: ApiSettings,
    client: LmStudioClient,
    diagnostics: StructlogDiagnosticsLog,
) -> ProposeGameRun:
    catalog = FilePromptPackageCatalog(settings.prompt_root)
    generation_config = TomlGenerationConfigurationResolver(settings.llm_config_path)
    story_initializer = InitializeStory(
        GenerateInitialStoryState(
            StoryInitializationPromptResolver(catalog),
            generation_config,
            LmStudioStoryInitializationAdapter(client),
            lambda: datetime.now(UTC),
            diagnostics,
        ),
        ExtractInitialWorldState(
            InitialExtractionPromptSelectionResolver(catalog),
            generation_config,
            LmStudioInitialWorldExtractionAdapter(client),
            diagnostics=diagnostics,
        ),
        diagnostics,
    )
    return ProposeGameRun(story_initializer, proposal_store, diagnostics=diagnostics)


def _compose_confirm_game_run_proposal(
    store: PostgresGameStore,
    proposal_store: InMemoryProposalStore,
    settings: ApiSettings,
    diagnostics: StructlogDiagnosticsLog,
) -> ConfirmGameRunProposal:
    validator = PromptProfileValidator(FilePromptPackageCatalog(settings.prompt_root))
    return ConfirmGameRunProposal(
        proposal_store,
        CreateGameRun(store, validator),
        diagnostics=diagnostics,
    )


def _compose_play_story_turn(
    store: PostgresGameStore,
    settings: ApiSettings,
    client: LmStudioClient,
    diagnostics: StructlogDiagnosticsLog,
) -> PlayStoryTurn:
    catalog = FilePromptPackageCatalog(settings.prompt_root)
    generation_config = TomlGenerationConfigurationResolver(settings.llm_config_path)
    return PlayStoryTurn(
        LoadGame(store, store),
        build_story_turn_context_selection(diagnostics=diagnostics),
        GenerateStory(
            StoryPromptSelectionResolver(catalog),
            generation_config,
            LmStudioStoryGenerationAdapter(client),
            diagnostics,
        ),
        ExtractStoryTurnChanges(
            ExtractionPromptSelectionResolver(catalog),
            generation_config,
            LmStudioTurnExtractionAdapter(client),
            diagnostics,
        ),
        ApproveStoryTurnChanges(diagnostics=diagnostics),
        SummarizeStory(
            SummaryPromptSelectionResolver(catalog),
            generation_config,
            LmStudioStorySummaryAdapter(client),
            diagnostics,
        ),
        CommitCompletedTurn(store, store, diagnostics),
        diagnostics=diagnostics,
    )


def _compose_start_playthrough(
    store: PostgresGameStore,
    settings: ApiSettings,
    diagnostics: StructlogDiagnosticsLog,
) -> StartPlaythrough:
    validator = PromptProfileValidator(FilePromptPackageCatalog(settings.prompt_root))
    return StartPlaythrough(
        LoadGame(store, store),
        CreateGameRun(store, validator),
        diagnostics=diagnostics,
    )


app = create_app()
