"""HTTP error mapping at the outermost application boundary."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from story_game.api.results import OperationFailed
from story_game.application.game_state import (
    RunConflict,
    RunNotFound,
    InvalidPromptPackageReference,
    InvalidPromptSelection,
    PromptPackageConfigurationInvalid,
    StateRejected,
    StateStoreUnavailable,
    StoredStateInvalid,
)
from story_game.domain.errors import DomainError, RevisionConflictError


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(OperationFailed, _operation_failed)
    app.add_exception_handler(RevisionConflictError, _conflict)
    app.add_exception_handler(DomainError, _domain_error)


async def _operation_failed(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, OperationFailed)
    error = exc.error
    if isinstance(error, RunNotFound):
        return _error_response(404, "not_found", error.detail)
    if isinstance(error, RunConflict):
        return _error_response(409, "revision_conflict", error.detail)
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
    raise exc


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
