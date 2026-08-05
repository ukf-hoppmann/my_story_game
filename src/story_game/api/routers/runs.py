"""Run and canonical-state HTTP endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from story_game.api.dependencies import ApiDependencies, get_api_dependencies
from story_game.api.mappers import (
    approved_changes_to_domain,
    state_from_api,
    state_to_api,
)
from story_game.api.schemas.changes import ApprovedChangeSetRequest
from story_game.api.schemas.state import StateDocument
from story_game.api.results import unwrap
from story_game.application.game_state import (
    CommitGameStateRequest,
    LoadGameStateRequest,
)
from story_game.domain import StableId, StateRevision


router = APIRouter()
runs_router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


@router.get("/health", tags=["system"], summary="Check API availability")
def health() -> dict[str, str]:
    return {"status": "ok"}


@runs_router.post(
    "",
    response_model=StateDocument,
    status_code=status.HTTP_201_CREATED,
    summary="Create an initial story-game run",
    description=(
        "Creates revision 1. The caller is responsible for supplying an "
        "application-approved initial canonical state."
    ),
)
def create_run(
    document: StateDocument,
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
) -> StateDocument:
    state = state_from_api(document, dependencies.state_codec)
    created = unwrap(dependencies.operations.create_initial.apply(state))
    return state_to_api(created, dependencies.state_codec)


@runs_router.get(
    "/{run_id}/state",
    response_model=StateDocument,
    summary="Load the current or a historical state revision",
)
def load_state(
    run_id: Annotated[str, Path(min_length=1)],
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    revision: Annotated[int | None, Query(ge=1)] = None,
) -> StateDocument:
    state = unwrap(
        dependencies.operations.load.apply(
            LoadGameStateRequest(
                StableId(run_id),
                None if revision is None else StateRevision(revision),
            )
        )
    )
    return state_to_api(state, dependencies.state_codec)


@runs_router.post(
    "/{run_id}/commits",
    response_model=StateDocument,
    summary="Commit an application-approved change set",
    description=(
        "The API accepts only an ApprovedChangeSet. Model prose or an "
        "unreviewed ProposedChangeSet is never written to the canonical state."
    ),
)
def commit_changes(
    run_id: Annotated[str, Path(min_length=1)],
    request: ApprovedChangeSetRequest,
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
) -> StateDocument:
    state = unwrap(
        dependencies.operations.commit.apply(
            CommitGameStateRequest(
                StableId(run_id),
                approved_changes_to_domain(request),
            )
        )
    )
    return state_to_api(state, dependencies.state_codec)


router.include_router(runs_router)
