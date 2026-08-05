"""HTTP error mapping at the outermost application boundary."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from story_game.domain.errors import DomainError, RevisionConflictError
from story_game.infrastructure.persistence.errors import (
    PersistenceConflictError,
    PersistenceConsistencyError,
    PersistenceError,
    PersistenceNotFoundError,
)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(PersistenceNotFoundError, _not_found)
    app.add_exception_handler(PersistenceConflictError, _conflict)
    app.add_exception_handler(RevisionConflictError, _conflict)
    app.add_exception_handler(PersistenceConsistencyError, _consistency)
    app.add_exception_handler(DomainError, _domain_error)
    app.add_exception_handler(PersistenceError, _persistence_error)


async def _not_found(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(404, "not_found", exc)


async def _conflict(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(409, "revision_conflict", exc)


async def _domain_error(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(422, "domain_validation_failed", exc)


async def _consistency(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(500, "persistence_consistency_failed", exc)


async def _persistence_error(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(503, "persistence_unavailable", exc)


def _error_response(status_code: int, error_type: str, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error_type,
            "detail": str(exc),
        },
    )
