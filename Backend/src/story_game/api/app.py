"""FastAPI composition root for the story-game run/turn API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from story_game.api.auth import KeycloakTokenVerifier
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
from story_game.application.diagnostics_reporting import ReportFrontendError
from story_game.application.story_initialization import GenerateInitialStoryState
from story_game.application.story_turn_context import build_story_turn_context_selection
from story_game.infrastructure.configuration import (
    TomlGenerationConfigurationResolver,
    TomlLlmConfigurationLoader,
)
from story_game.infrastructure.diagnostics import StructlogDiagnosticsLog
from story_game.infrastructure.llm import FilePromptPackageCatalog
from story_game.infrastructure.llm.gemini import (
    GeminiInitialWorldExtractionAdapter,
    GeminiStoryGenerationAdapter,
    GeminiStoryInitializationAdapter,
    GeminiStorySummaryAdapter,
    GeminiTurnExtractionAdapter,
    gemini_settings,
)
from story_game.infrastructure.llm.groq import (
    GroqInitialWorldExtractionAdapter,
    GroqStoryGenerationAdapter,
    GroqStoryInitializationAdapter,
    GroqStorySummaryAdapter,
    GroqTurnExtractionAdapter,
    groq_settings,
)
from story_game.infrastructure.llm.lmstudio import (
    LmStudioInitialWorldExtractionAdapter,
    LmStudioStoryGenerationAdapter,
    LmStudioStoryInitializationAdapter,
    LmStudioStorySummaryAdapter,
    LmStudioTurnExtractionAdapter,
    lmstudio_settings,
)
from story_game.infrastructure.llm.openai_compatible import (
    OpenAiCompatibleClient,
    OpenAiCompatibleSettings,
)
from story_game.infrastructure.llm.provider_router import (
    RoutingInitialWorldExtractionAdapter,
    RoutingStoryGenerationAdapter,
    RoutingStoryInitializationAdapter,
    RoutingStorySummaryAdapter,
    RoutingTurnExtractionAdapter,
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
        llm_clients: _LlmClients | None = None
        if resolved is None:
            connections = PostgresConnectionFactory(resolved_settings.postgres_dsn)
            if resolved_settings.auto_migrate:
                PostgresSchemaMigrator(connections).migrate()
            store = PostgresGameStore(connections)
            proposal_store = InMemoryProposalStore()
            llm_clients = _build_llm_clients(resolved_settings)
            resolved = ApiDependencies(
                operations=_compose_game_state_operations(
                    store, resolved_settings.prompt_root, diagnostics
                ),
                propose_run=_compose_propose_game_run(
                    proposal_store, resolved_settings, llm_clients, diagnostics
                ),
                confirm_proposal=_compose_confirm_game_run_proposal(
                    store, proposal_store, resolved_settings, diagnostics
                ),
                play_turn=_compose_play_story_turn(
                    store, resolved_settings, llm_clients, diagnostics
                ),
                start_playthrough=_compose_start_playthrough(
                    store, resolved_settings, diagnostics
                ),
                prompt_catalog=FilePromptPackageCatalog(resolved_settings.prompt_root),
                prompt_profile_validator=PromptProfileValidator(
                    FilePromptPackageCatalog(resolved_settings.prompt_root)
                ),
                report_frontend_error=_compose_report_frontend_error(diagnostics),
            )
        application.state.api_dependencies = resolved
        application.state.api_settings = resolved_settings
        application.state.token_verifier = KeycloakTokenVerifier(
            resolved_settings.keycloak_issuer,
            resolved_settings.keycloak_audience,
            jwks_uri=resolved_settings.keycloak_jwks_uri,
        )
        try:
            yield
        finally:
            if llm_clients is not None:
                llm_clients.lmstudio.close()
                llm_clients.groq.close()
                llm_clients.gemini.close()

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


def _compose_report_frontend_error(
    diagnostics: StructlogDiagnosticsLog,
) -> ReportFrontendError:
    return ReportFrontendError(diagnostics)


@dataclass(frozen=True, slots=True)
class _LlmClients:
    """Every provider transport, built once and reused across every task.

    Building all of them unconditionally — even when a fresh install only
    ever routes to one — keeps Composition Root simple and matches how
    ``RoutingXAdapter`` picks between pre-built adapters per call rather than
    constructing a client per request. After the shared-core refactor, every
    provider uses the same ``OpenAiCompatibleClient``, differing only in
    which settings-resolver closure it was built with. No client resolves
    its settings (base_url, api_key) until a request actually goes out, so
    an unconfigured provider (e.g. no Groq key yet) does not prevent
    startup — see ``OpenAiCompatibleClient.complete``.
    """

    lmstudio: OpenAiCompatibleClient
    groq: OpenAiCompatibleClient
    gemini: OpenAiCompatibleClient


def _build_llm_clients(settings: ApiSettings) -> _LlmClients:
    def resolve_lmstudio_settings() -> OpenAiCompatibleSettings:
        # Reloaded on every call so that changes to configs/llm.toml (base_url,
        # timeout) take effect without restarting the server, matching the
        # per-call reload already used for task/model selection.
        runtime_configuration = TomlLlmConfigurationLoader().load(settings.llm_config_path)
        provider = runtime_configuration.provider("lmstudio")
        return lmstudio_settings(provider.base_url, timeout_seconds=provider.timeout_seconds)

    def resolve_groq_settings() -> OpenAiCompatibleSettings:
        runtime_configuration = TomlLlmConfigurationLoader().load(settings.llm_config_path)
        provider = runtime_configuration.provider("groq")
        return groq_settings(
            provider.base_url,
            api_token=provider.api_key,
            timeout_seconds=provider.timeout_seconds,
        )

    def resolve_gemini_settings() -> OpenAiCompatibleSettings:
        runtime_configuration = TomlLlmConfigurationLoader().load(settings.llm_config_path)
        provider = runtime_configuration.provider("gemini")
        return gemini_settings(
            provider.base_url,
            api_token=provider.api_key,
            timeout_seconds=provider.timeout_seconds,
        )

    return _LlmClients(
        lmstudio=OpenAiCompatibleClient(resolve_lmstudio_settings),
        groq=OpenAiCompatibleClient(resolve_groq_settings),
        gemini=OpenAiCompatibleClient(resolve_gemini_settings),
    )


def _compose_propose_game_run(
    proposal_store: InMemoryProposalStore,
    settings: ApiSettings,
    clients: _LlmClients,
    diagnostics: StructlogDiagnosticsLog,
) -> ProposeGameRun:
    catalog = FilePromptPackageCatalog(settings.prompt_root)
    generation_config = TomlGenerationConfigurationResolver(settings.llm_config_path)
    story_initializer = InitializeStory(
        GenerateInitialStoryState(
            StoryInitializationPromptResolver(catalog),
            generation_config,
            RoutingStoryInitializationAdapter(
                {
                    "lmstudio": LmStudioStoryInitializationAdapter(clients.lmstudio),
                    "groq": GroqStoryInitializationAdapter(clients.groq),
                    "gemini": GeminiStoryInitializationAdapter(clients.gemini),
                }
            ),
            lambda: datetime.now(UTC),
            diagnostics,
        ),
        ExtractInitialWorldState(
            InitialExtractionPromptSelectionResolver(catalog),
            generation_config,
            RoutingInitialWorldExtractionAdapter(
                {
                    "lmstudio": LmStudioInitialWorldExtractionAdapter(clients.lmstudio),
                    "groq": GroqInitialWorldExtractionAdapter(clients.groq),
                    "gemini": GeminiInitialWorldExtractionAdapter(clients.gemini),
                }
            ),
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
    clients: _LlmClients,
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
            RoutingStoryGenerationAdapter(
                {
                    "lmstudio": LmStudioStoryGenerationAdapter(clients.lmstudio),
                    "groq": GroqStoryGenerationAdapter(clients.groq),
                    "gemini": GeminiStoryGenerationAdapter(clients.gemini),
                }
            ),
            diagnostics,
        ),
        ExtractStoryTurnChanges(
            ExtractionPromptSelectionResolver(catalog),
            generation_config,
            RoutingTurnExtractionAdapter(
                {
                    "lmstudio": LmStudioTurnExtractionAdapter(clients.lmstudio),
                    "groq": GroqTurnExtractionAdapter(clients.groq),
                    "gemini": GeminiTurnExtractionAdapter(clients.gemini),
                }
            ),
            diagnostics,
        ),
        ApproveStoryTurnChanges(diagnostics=diagnostics),
        SummarizeStory(
            SummaryPromptSelectionResolver(catalog),
            generation_config,
            RoutingStorySummaryAdapter(
                {
                    "lmstudio": LmStudioStorySummaryAdapter(clients.lmstudio),
                    "groq": GroqStorySummaryAdapter(clients.groq),
                    "gemini": GeminiStorySummaryAdapter(clients.gemini),
                }
            ),
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
