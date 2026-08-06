"""Temporary full-state HTTP endpoints used to exercise persistence."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from story_game.api.dependencies import ApiDependencies, get_api_dependencies
from story_game.api.mappers import game_from_api, game_to_api
from story_game.api.results import unwrap
from story_game.api.schemas.state import GameDocument
from story_game.application.game_state import (
    CreateGameRunRequest,
    LoadGameRequest,
)
from story_game.domain import StableId, StateRevision


router = APIRouter()
runs_router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


@router.get("/health", tags=["system"], summary="Check API availability")
def health() -> dict[str, str]:
    return {"status": "ok"}


@runs_router.post(
    "",
    response_model=GameDocument,
    status_code=status.HTTP_201_CREATED,
    summary="Store a complete initial test state",
)
def create_run(
    document: GameDocument,
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
) -> GameDocument:
    game = game_from_api(document)
    created = unwrap(
        dependencies.operations.create.apply(
            CreateGameRunRequest(game.run, game.state)
        )
    )
    return game_to_api(created)


@runs_router.get(
    "/{run_id}/state",
    response_model=GameDocument,
    summary="Load a complete current or historical test state",
)
def load_state(
    run_id: Annotated[str, Path(min_length=1)],
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    revision: Annotated[int | None, Query(ge=1)] = None,
) -> GameDocument:
    loaded = unwrap(
        dependencies.operations.load.apply(
            LoadGameRequest(
                StableId(run_id),
                None if revision is None else StateRevision(revision),
            )
        )
    )
    return game_to_api(loaded)


router.include_router(runs_router)
