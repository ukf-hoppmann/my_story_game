"""Endpoint for the frontend to report its own tooling-side failures.

TASK-030: deliberately requires the same Keycloak Bearer token as every
other run/turn endpoint (unlike ``prompt_profile.py``'s public catalog) —
``401``s are handled by the frontend as a forced re-login instead of being
reported here, so by the time a tooling error is worth reporting a valid
token still exists. See ``application/diagnostics_reporting.py``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from story_game.api.dependencies import (
    ApiDependencies,
    get_api_dependencies,
    get_current_initiator,
)
from story_game.api.results import unwrap
from story_game.api.schemas.diagnostics import FrontendErrorReportModel
from story_game.application import RunInitiator
from story_game.application.diagnostics_reporting import ReportFrontendErrorRequest

router = APIRouter(prefix="/api/v1/diagnostics", tags=["diagnostics"])


@router.post(
    "/frontend-errors",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Report a tooling-side frontend error for diagnostics",
)
def report_frontend_error(
    payload: FrontendErrorReportModel,
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    _initiator: Annotated[RunInitiator, Depends(get_current_initiator)],
) -> None:
    unwrap(
        dependencies.report_frontend_error.apply(
            ReportFrontendErrorRequest(
                source=payload.source,
                message=payload.message,
                url=payload.url,
                user_agent=payload.user_agent,
            )
        )
    )
