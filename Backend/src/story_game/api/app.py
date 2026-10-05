"""FastAPI composition root for the story-game run/turn API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from story_game.api.auth import KeycloakTokenVerifier
from story_game.api.dependencies import ApiDependencies
from story_game.application import (
    ConfirmGameRunProposal,
    ExtractInitialWorldState,
    ExtractStoryTurnChanges,
    Failure,
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
    GenerationConfigurationResolver,
    PromptPackageCatalog,
    CompactImagePromptResolver,
    ExtractionPromptSelectionResolver,
    SceneImagePromptResolver,
    InitialExtractionPromptSelectionResolver,
    StoryInitializationPromptResolver,
    StoryPromptSelectionResolver,
    SummaryPromptSelectionResolver,
)
from story_game.application.diagnostics_reporting import ReportFrontendError
from story_game.application.model_settings import (
    ListModelSettingHistory,
    ListModelSettings,
    ManagedGenerationConfigurationResolver,
    ModelSettingsOperations,
    ResetModelSettings,
    SeedModelSettings,
    SeedModelSettingsRequest,
    UpdateModelSetting,
)
from story_game.application.prompt_management import (
    CreatePromptOption,
    ListCustomPromptOptions,
    ListPromptEntries,
    ListPromptHistory,
    PromptManagementOperations,
    PromptOptionUsage,
    RemovePromptOptions,
    RestorePromptOption,
    PurgePromptOption,
    ListArchivedPromptOptions,
    ArchivePromptOption,
    ResetPromptText,
    SeedPromptPackages,
    SeedPromptPackagesRequest,
    UpdatePromptText,
)
from story_game.application.scene_image import (
    GenerateSceneImage,
    ListSceneImages,
    LoadSceneImage,
    LoadSceneImageContent,
    ReadSceneImageCapabilities,
    RequestSceneImage,
    SceneImageDefaults,
    SceneImageOperations,
)
from story_game.domain import StableId
from story_game.application.story_initialization import GenerateInitialStoryState
from story_game.application.story_turn_context import build_story_turn_context_selection
from story_game.application.story_turn_context_models import SelectionBudget
from story_game.infrastructure.configuration import (
    SceneImageSettings,
    TomlAppConfigurationLoader,
    load_modal_credentials,
    TomlModelSettingsSource,
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
from story_game.infrastructure.image import ModalSceneImageRenderer
from story_game.infrastructure.llm.openai_compatible import (
    OpenAiCompatibleClient,
    OpenAiCompatibleSettings,
)
from story_game.infrastructure.llm.openai_compatible.scene_image_adapters import (
    OpenAiCompatibleCompactImagePromptAdapter,
    OpenAiCompatibleSceneImagePromptAdapter,
)
from story_game.infrastructure.llm.provider_router import (
    RoutingCompactImagePromptAdapter,
    RoutingInitialWorldExtractionAdapter,
    RoutingSceneImagePromptAdapter,
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
    DbPromptPackageCatalog,
    PostgresConnectionFactory,
    PostgresGameStore,
    PostgresModelSettingsStore,
    PostgresPromptOptionUsage,
    PostgresPromptStore,
    PostgresSceneImageStore,
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
        modal_renderer: ModalSceneImageRenderer | None = None
        if resolved is None:
            connections = PostgresConnectionFactory(resolved_settings.postgres_dsn)
            if resolved_settings.auto_migrate:
                PostgresSchemaMigrator(connections).migrate()
            store = PostgresGameStore(connections)
            prompt_store = PostgresPromptStore(connections)
            _seed_prompts(resolved_settings, prompt_store)
            prompt_catalog = DbPromptPackageCatalog(prompt_store)
            model_store = PostgresModelSettingsStore(connections)
            model_source = TomlModelSettingsSource(resolved_settings.llm_config_path)
            _seed_model_settings(model_source, model_store)
            generation_config = ManagedGenerationConfigurationResolver(model_store, model_source)
            proposal_store = InMemoryProposalStore()
            llm_clients = _build_llm_clients(
                resolved_settings, debug_enabled=resolved_logging_settings.debug_enabled
            )
            scene_image_settings = TomlAppConfigurationLoader().load_scene_image(
                resolved_settings.config_path
            )
            scene_images = None
            if scene_image_settings.enabled:
                modal_renderer = _build_modal_renderer(
                    scene_image_settings, resolved_settings.config_path
                )
                scene_images = _compose_scene_images(
                    store,
                    PostgresSceneImageStore(connections),
                    modal_renderer,
                    scene_image_settings,
                    resolved_settings,
                    prompt_catalog,
                    generation_config,
                    llm_clients,
                    diagnostics,
                )
            resolved = ApiDependencies(
                operations=_compose_game_state_operations(
                    store, prompt_catalog, diagnostics
                ),
                propose_run=_compose_propose_game_run(
                    proposal_store,
                    resolved_settings,
                    prompt_catalog,
                    generation_config,
                    llm_clients,
                    diagnostics,
                ),
                confirm_proposal=_compose_confirm_game_run_proposal(
                    store, proposal_store, prompt_catalog, diagnostics
                ),
                play_turn=_compose_play_story_turn(
                    store,
                    resolved_settings,
                    prompt_catalog,
                    generation_config,
                    llm_clients,
                    diagnostics,
                ),
                start_playthrough=_compose_start_playthrough(
                    store, prompt_catalog, diagnostics
                ),
                prompt_catalog=prompt_catalog,
                prompt_profile_validator=PromptProfileValidator(prompt_catalog),
                report_frontend_error=_compose_report_frontend_error(diagnostics),
                scene_images=scene_images,
                prompt_management=_compose_prompt_management(
                    resolved_settings, prompt_store, PostgresPromptOptionUsage(connections)
                ),
                model_settings=_compose_model_settings(model_source, model_store),
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
            if modal_renderer is not None:
                modal_renderer.close()

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


def _seed_prompts(settings: ApiSettings, prompt_store: PostgresPromptStore) -> None:
    """Import the shipped TOML prompt packages the database does not hold yet.

    Only a package without any stored version is imported, so a restart never
    overwrites prompts edited in the UI. A failure is fatal: without prompts
    no story can be generated.
    """
    result = SeedPromptPackages(
        FilePromptPackageCatalog(settings.prompt_root),
        prompt_store,
        prompt_store,
        StableId.new,
        lambda: datetime.now(UTC),
    ).apply(SeedPromptPackagesRequest())
    if isinstance(result, Failure):
        raise RuntimeError(f"Die Prompts konnten nicht initialisiert werden: {result.error.message}")


def _seed_model_settings(
    source: TomlModelSettingsSource, model_store: PostgresModelSettingsStore
) -> None:
    """Import the task models of llm.toml for every task the database has none for.

    A restart never overwrites a choice made in the UI. A failure is fatal:
    without a model setting no task can be generated.
    """
    result = SeedModelSettings(
        source, model_store, model_store, StableId.new, lambda: datetime.now(UTC)
    ).apply(SeedModelSettingsRequest())
    if isinstance(result, Failure):
        raise RuntimeError(
            f"Die Modelleinstellungen konnten nicht initialisiert werden: {result.error.message}"
        )


def _compose_model_settings(
    source: TomlModelSettingsSource, model_store: PostgresModelSettingsStore
) -> ModelSettingsOperations:
    clock = lambda: datetime.now(UTC)  # noqa: E731
    return ModelSettingsOperations(
        overview=ListModelSettings(model_store, source),
        history=ListModelSettingHistory(model_store),
        update=UpdateModelSetting(model_store, model_store, source, StableId.new, clock),
        reset=ResetModelSettings(source, model_store, model_store, StableId.new, clock),
    )


def _compose_prompt_management(
    settings: ApiSettings, prompt_store: PostgresPromptStore, option_usage: PromptOptionUsage
) -> PromptManagementOperations:
    source = FilePromptPackageCatalog(settings.prompt_root)
    clock = lambda: datetime.now(UTC)  # noqa: E731
    archive = ArchivePromptOption(source, prompt_store, prompt_store, option_usage)
    purge = PurgePromptOption(prompt_store, prompt_store)
    archived = ListArchivedPromptOptions(prompt_store)
    return PromptManagementOperations(
        entries=ListPromptEntries(prompt_store),
        history=ListPromptHistory(prompt_store),
        update=UpdatePromptText(prompt_store, prompt_store, StableId.new, clock),
        reset=ResetPromptText(source, prompt_store, prompt_store, StableId.new, clock),
        create_option=CreatePromptOption(prompt_store, prompt_store, StableId.new, clock),
        custom_options=ListCustomPromptOptions(source, prompt_store),
        archive_option=archive,
        restore_option=RestorePromptOption(prompt_store, prompt_store),
        purge_option=purge,
        archived_options=archived,
        remove_options=RemovePromptOptions(
            archive, purge, ListCustomPromptOptions(source, prompt_store), archived
        ),
    )


def _compose_game_state_operations(
    store: PostgresGameStore,
    catalog: PromptPackageCatalog,
    diagnostics: StructlogDiagnosticsLog,
) -> GameStateOperations:
    validator = PromptProfileValidator(catalog)
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


def _build_llm_clients(settings: ApiSettings, *, debug_enabled: bool) -> _LlmClients:
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
        lmstudio=OpenAiCompatibleClient(resolve_lmstudio_settings, debug_enabled=debug_enabled),
        groq=OpenAiCompatibleClient(resolve_groq_settings, debug_enabled=debug_enabled),
        gemini=OpenAiCompatibleClient(resolve_gemini_settings, debug_enabled=debug_enabled),
    )


def _compose_propose_game_run(
    proposal_store: InMemoryProposalStore,
    settings: ApiSettings,
    catalog: PromptPackageCatalog,
    generation_config: GenerationConfigurationResolver,
    clients: _LlmClients,
    diagnostics: StructlogDiagnosticsLog,
) -> ProposeGameRun:
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
    catalog: PromptPackageCatalog,
    diagnostics: StructlogDiagnosticsLog,
) -> ConfirmGameRunProposal:
    validator = PromptProfileValidator(catalog)
    return ConfirmGameRunProposal(
        proposal_store,
        CreateGameRun(store, validator),
        diagnostics=diagnostics,
    )


def _compose_play_story_turn(
    store: PostgresGameStore,
    settings: ApiSettings,
    catalog: PromptPackageCatalog,
    generation_config: GenerationConfigurationResolver,
    clients: _LlmClients,
    diagnostics: StructlogDiagnosticsLog,
) -> PlayStoryTurn:
    summary_settings = TomlAppConfigurationLoader().load_story_summary(
        settings.config_path
    )
    return PlayStoryTurn(
        LoadGame(store, store),
        build_story_turn_context_selection(
            budget=SelectionBudget(
                summary_segment_count=summary_settings.context_segment_count
            ),
            diagnostics=diagnostics,
        ),
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
        summary_interval=summary_settings.interval,
        diagnostics=diagnostics,
    )


def _build_modal_renderer(
    scene_settings: SceneImageSettings, config_path: str
) -> ModalSceneImageRenderer:
    modal = scene_settings.modal
    assert modal is not None  # the loader rejects an enabled feature without it
    return ModalSceneImageRenderer(
        lambda: modal,
        # Reloaded per call so a rotated token takes effect without a restart.
        lambda: load_modal_credentials(config_path),
        httpx.Client(),
    )


def _compose_scene_images(
    game_store: PostgresGameStore,
    image_store: PostgresSceneImageStore,
    renderer: ModalSceneImageRenderer,
    scene_settings: SceneImageSettings,
    settings: ApiSettings,
    catalog: PromptPackageCatalog,
    generation_config: GenerationConfigurationResolver,
    clients: _LlmClients,
    diagnostics: StructlogDiagnosticsLog,
) -> SceneImageOperations:
    modal = scene_settings.modal
    assert modal is not None
    defaults = SceneImageDefaults(
        turn_window=scene_settings.turn_window,
        width=scene_settings.width,
        height=scene_settings.height,
        model=modal.model,
        refine=scene_settings.refine,
        refine_model=scene_settings.refine_model,
        refine_strength=scene_settings.refine_strength,
        compact_prompt_max_words=scene_settings.compact_prompt_max_words,
    )
    providers = (
        ("lmstudio", "LM Studio", clients.lmstudio),
        ("groq", "Groq", clients.groq),
        ("gemini", "Gemini", clients.gemini),
    )
    prompt_writer = RoutingSceneImagePromptAdapter(
        {
            provider_id: OpenAiCompatibleSceneImagePromptAdapter(client, provider_id, label)
            for provider_id, label, client in providers
        }
    )
    compactor = RoutingCompactImagePromptAdapter(
        {
            provider_id: OpenAiCompatibleCompactImagePromptAdapter(client, provider_id, label)
            for provider_id, label, client in providers
        }
    )
    return SceneImageOperations(
        request=RequestSceneImage(
            LoadGame(game_store, game_store),
            image_store,
            defaults,
            new_id=lambda: StableId(uuid4()),
            now=lambda: datetime.now(UTC),
            # A pending image older than the longest possible generation
            # (prompt calls plus two Modal stages) is treated as abandoned,
            # e.g. after a server restart, so it cannot block its turn forever.
            active_window=timedelta(seconds=2 * modal.timeout_seconds + 120),
        ),
        generate=GenerateSceneImage(
            SceneImagePromptResolver(catalog),
            CompactImagePromptResolver(catalog),
            generation_config,
            prompt_writer,
            compactor,
            renderer,
            image_store,
            compact_prompt_max_words=scene_settings.compact_prompt_max_words,
            now=lambda: datetime.now(UTC),
            diagnostics=diagnostics,
        ),
        list=ListSceneImages(image_store),
        load=LoadSceneImage(image_store),
        content=LoadSceneImageContent(image_store),
        capabilities=ReadSceneImageCapabilities(defaults, renderer),
    )


def _compose_start_playthrough(
    store: PostgresGameStore,
    catalog: PromptPackageCatalog,
    diagnostics: StructlogDiagnosticsLog,
) -> StartPlaythrough:
    validator = PromptProfileValidator(catalog)
    return StartPlaythrough(
        LoadGame(store, store),
        CreateGameRun(store, validator),
        diagnostics=diagnostics,
    )


app = create_app()
