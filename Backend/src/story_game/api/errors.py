"""HTTP error mapping at the outermost application boundary."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from story_game.api.results import OperationFailed
from story_game.application.diagnostics_reporting import ReportFrontendErrorRejected
from story_game.application.game_state import (
    RunAccessDenied,
    RunConflict,
    RunNotFound,
    InvalidPromptPackageReference,
    InvalidPromptSelection,
    PromptPackageConfigurationInvalid,
    StateRejected,
    StateStoreUnavailable,
    StoredStateInvalid,
)
from story_game.application.initialization_errors import (
    StoryInitializationError,
    StoryInitializationErrorKind,
)
from story_game.application.model_settings import ModelSettingsError, ModelSettingsErrorKind
from story_game.application.prompt_management import (
    PromptManagementError,
    PromptManagementErrorKind,
)
from story_game.application.scene_image import SceneImageError, SceneImageErrorKind
from story_game.application.start_playthrough_errors import (
    PlaythroughError,
    PlaythroughErrorKind,
)
from story_game.application.story_turn_context_errors import ContextSelectionError
from story_game.application.story_turn_errors import StoryTurnError, StoryTurnErrorKind
from story_game.domain.errors import DomainError, RevisionConflictError

_STORY_INIT_STATUS: dict[StoryInitializationErrorKind, tuple[int, str]] = {
    StoryInitializationErrorKind.INVALID_CONFIGURATION: (
        500,
        "story_configuration_invalid",
    ),
    StoryInitializationErrorKind.MISSING_PLAYER_CHARACTER: (
        422,
        "invalid_player_character_seed",
    ),
    StoryInitializationErrorKind.DUPLICATE_CONTROLLABLE_CHARACTER: (
        422,
        "invalid_player_character_seed",
    ),
    StoryInitializationErrorKind.MODEL_FAILURE: (502, "story_model_unavailable"),
    StoryInitializationErrorKind.INVALID_MODEL_RESPONSE: (
        502,
        "story_model_unavailable",
    ),
    StoryInitializationErrorKind.INVALID_CANDIDATE_REFERENCE: (
        500,
        "story_initialization_inconsistent",
    ),
    StoryInitializationErrorKind.DOMAIN_REJECTION: (422, "domain_validation_failed"),
}

_STORY_TURN_STATUS: dict[StoryTurnErrorKind, tuple[int, str]] = {
    StoryTurnErrorKind.INVALID_CONFIGURATION: (500, "story_configuration_invalid"),
    StoryTurnErrorKind.MODEL_FAILURE: (502, "story_model_unavailable"),
    StoryTurnErrorKind.INVALID_MODEL_RESPONSE: (502, "story_model_unavailable"),
    StoryTurnErrorKind.INVALID_CANDIDATE_REFERENCE: (500, "story_turn_inconsistent"),
    StoryTurnErrorKind.DOMAIN_REJECTION: (422, "domain_validation_failed"),
    StoryTurnErrorKind.UNKNOWN_MEMBER: (403, "not_a_run_member"),
    StoryTurnErrorKind.RUN_NOT_ACTIVE: (409, "run_not_active"),
}

_PLAYTHROUGH_STATUS: dict[PlaythroughErrorKind, tuple[int, str]] = {
    PlaythroughErrorKind.SOURCE_NOT_DRAFT: (409, "playthrough_source_not_draft"),
}


_SCENE_IMAGE_STATUS: dict[SceneImageErrorKind, tuple[int, str]] = {
    SceneImageErrorKind.DISABLED: (409, "scene_image_disabled"),
    SceneImageErrorKind.NO_STORY: (422, "scene_image_no_story"),
    SceneImageErrorKind.NOT_FOUND: (404, "not_found"),
    SceneImageErrorKind.INVALID_OPTIONS: (422, "scene_image_invalid_options"),
    SceneImageErrorKind.ACCESS_DENIED: (403, "not_a_run_member"),
    SceneImageErrorKind.STORE_UNAVAILABLE: (503, "persistence_unavailable"),
    SceneImageErrorKind.PROMPT_FAILED: (502, "scene_image_failed"),
    SceneImageErrorKind.RENDER_FAILED: (502, "scene_image_failed"),
    SceneImageErrorKind.CONFIGURATION: (500, "scene_image_configuration_invalid"),
}

_PROMPT_MANAGEMENT_STATUS: dict[PromptManagementErrorKind, tuple[int, str]] = {
    PromptManagementErrorKind.NOT_FOUND: (404, "not_found"),
    PromptManagementErrorKind.INVALID_TEXT: (422, "invalid_prompt_text"),
    PromptManagementErrorKind.INVALID_OPTION: (422, "invalid_prompt_option"),
    PromptManagementErrorKind.ALREADY_EXISTS: (409, "prompt_option_exists"),
    PromptManagementErrorKind.NOT_REMOVABLE: (409, "prompt_option_not_removable"),
    PromptManagementErrorKind.IN_USE: (409, "prompt_option_in_use"),
    PromptManagementErrorKind.SOURCE_UNAVAILABLE: (500, "prompt_source_unavailable"),
    PromptManagementErrorKind.STORE_UNAVAILABLE: (503, "persistence_unavailable"),
}

_MODEL_SETTINGS_STATUS: dict[ModelSettingsErrorKind, tuple[int, str]] = {
    ModelSettingsErrorKind.NOT_FOUND: (404, "not_found"),
    ModelSettingsErrorKind.INVALID_MODEL: (422, "invalid_model_selection"),
    ModelSettingsErrorKind.INVALID_OPTIONS: (422, "invalid_generation_options"),
    ModelSettingsErrorKind.SOURCE_UNAVAILABLE: (500, "model_catalog_unavailable"),
    ModelSettingsErrorKind.STORE_UNAVAILABLE: (503, "persistence_unavailable"),
}


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(OperationFailed, _operation_failed)
    app.add_exception_handler(RevisionConflictError, _conflict)
    app.add_exception_handler(DomainError, _domain_error)
    app.add_exception_handler(HTTPException, _http_exception)


async def _operation_failed(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, OperationFailed)
    error = exc.error
    if isinstance(error, RunNotFound):
        return _error_response(404, "not_found", error.detail)
    if isinstance(error, RunConflict):
        return _error_response(409, "revision_conflict", error.detail)
    if isinstance(error, RunAccessDenied):
        return _error_response(403, "not_a_run_member", error.detail)
    if isinstance(error, StateRejected):
        return _error_response(422, "domain_validation_failed", error.detail)
    if isinstance(error, InvalidPromptSelection):
        return _error_response(
            422,
            "invalid_prompt_selection",
            error.detail,
            category=error.category,
            option_id=error.option_id,
        )
    if isinstance(error, InvalidPromptPackageReference):
        return _error_response(422, "invalid_prompt_package_reference", error.detail)
    if isinstance(error, PromptPackageConfigurationInvalid):
        return _error_response(500, "prompt_package_configuration_invalid", error.detail)
    if isinstance(error, StoredStateInvalid):
        return _error_response(500, "persistence_consistency_failed", error.detail)
    if isinstance(error, StateStoreUnavailable):
        return _error_response(503, "persistence_unavailable", error.detail)
    if isinstance(error, StoryInitializationError):
        status_code, code = _STORY_INIT_STATUS[error.kind]
        return _error_response(status_code, code, error.message)
    if isinstance(error, StoryTurnError):
        status_code, code = _STORY_TURN_STATUS[error.kind]
        return _error_response(status_code, code, error.message)
    if isinstance(error, ContextSelectionError):
        return _error_response(500, "story_turn_inconsistent", error.message)
    if isinstance(error, PlaythroughError):
        status_code, code = _PLAYTHROUGH_STATUS[error.kind]
        return _error_response(status_code, code, error.message)
    if isinstance(error, SceneImageError):
        status_code, code = _SCENE_IMAGE_STATUS[error.kind]
        return _error_response(status_code, code, error.message)
    if isinstance(error, ModelSettingsError):
        status_code, code = _MODEL_SETTINGS_STATUS[error.kind]
        return _error_response(status_code, code, error.message)
    if isinstance(error, PromptManagementError):
        status_code, code = _PROMPT_MANAGEMENT_STATUS[error.kind]
        return _error_response(status_code, code, error.message)
    if isinstance(error, ReportFrontendErrorRejected):
        return _error_response(400, "invalid_frontend_error_report", error.detail)
    raise exc


async def _http_exception(request: Request, exc: Exception) -> JSONResponse:
    """Keep the ``{error, detail}`` envelope for framework-raised HTTP errors.

    Mostly ``get_current_initiator`` (missing/invalid Bearer token, HTTP
    401) and ``require_admin`` (missing admin role, HTTP 403) plus the prompt-profile catalog endpoint's fixed-package lookup
    (HTTP 500, no ``.apply()`` call involved) — everything else goes
    through the typed ``OperationFailed``/``DomainError`` paths above. Any
    other status here (e.g. Starlette's own 404/405) falls back to a
    generic code.
    """
    assert isinstance(exc, HTTPException)
    code = {401: "unauthorized", 403: "forbidden"}.get(exc.status_code, "http_error")
    return _error_response(exc.status_code, code, exc.detail)


async def _conflict(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(409, "revision_conflict", exc)


async def _domain_error(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(422, "domain_validation_failed", exc)


def _error_response(
    status_code: int, error_type: str, detail: Exception | str, **context: str
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error_type,
            "detail": str(detail),
            **context,
        },
    )
