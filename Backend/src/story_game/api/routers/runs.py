"""HTTP endpoints for listing, loading, starting, and playing story-game runs."""

from __future__ import annotations

from dataclasses import replace
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status

from story_game.api.default_configuration import DEFAULT_GAME_CONFIGURATION
from story_game.api.dependencies import (
    ApiDependencies,
    get_api_dependencies,
    get_current_initiator,
)
from story_game.api.mappers import game_state_to_api, game_to_api
from story_game.api.results import unwrap
from story_game.api.schemas.runs import (
    InitializeRunRequestModel,
    PlayTurnRequestModel,
    RunSummaryListModel,
    RunSummaryModel,
    TurnResultModel,
)
from story_game.api.schemas.state import GameDocument
from story_game.application import (
    InitializeGameRunRequest,
    ControllableCharacterSeed,
    PlayStoryTurnRequest,
    RunInitiator,
    StartPlaythroughRequest,
)
from story_game.application.game_state import LoadGameRequest, ListPlayableRunsRequest
from story_game.domain import StableId, StateRevision


router = APIRouter()
runs_router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


@router.get("/health", tags=["system"], summary="Check API availability")
def health() -> dict[str, str]:
    return {"status": "ok"}


@runs_router.get(
    "",
    response_model=RunSummaryListModel,
    summary="List the caller's DRAFT templates and ACTIVE playthroughs",
)
def list_runs(
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    initiator: Annotated[RunInitiator, Depends(get_current_initiator)],
) -> RunSummaryListModel:
    summaries = unwrap(
        dependencies.operations.list_playable_runs.apply(
            ListPlayableRunsRequest(initiator.issuer, initiator.subject)
        )
    )
    return RunSummaryListModel(
        runs=[
            RunSummaryModel(
                id=summary.run_id.value,
                name=summary.name,
                status=summary.status,
                current_revision=summary.current_revision.value,
                game_role=summary.game_role,
                updated_at=summary.updated_at,
            )
            for summary in summaries
        ]
    )


@runs_router.get(
    "/{run_id}",
    response_model=GameDocument,
    summary="Load a run's current or historical state",
)
def load_run(
    run_id: Annotated[UUID, Path()],
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


@runs_router.post(
    "",
    response_model=GameDocument,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new DRAFT scenario template",
)
def create_run(
    payload: InitializeRunRequestModel,
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    initiator: Annotated[RunInitiator, Depends(get_current_initiator)],
) -> GameDocument:
    configuration = replace(
        DEFAULT_GAME_CONFIGURATION,
        prompt_profile=replace(
            DEFAULT_GAME_CONFIGURATION.prompt_profile,
            control_mode=payload.control_mode,
        ),
    )
    controllable_characters = tuple(
        ControllableCharacterSeed(item.name, item.description)
        for item in payload.controllable_characters
    )
    created = unwrap(
        dependencies.initialize_run.apply(
            InitializeGameRunRequest(
                configuration=configuration,
                run_name=payload.run_name,
                initial_prompt=payload.initial_prompt,
                initiator=initiator,
                controllable_characters=controllable_characters,
            )
        )
    )
    return game_to_api(created)


@runs_router.post(
    "/{run_id}/playthroughs",
    response_model=GameDocument,
    status_code=status.HTTP_201_CREATED,
    summary="Fork a DRAFT template into a new independent ACTIVE playthrough",
)
def start_playthrough(
    run_id: Annotated[UUID, Path()],
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    initiator: Annotated[RunInitiator, Depends(get_current_initiator)],
) -> GameDocument:
    created = unwrap(
        dependencies.start_playthrough.apply(
            StartPlaythroughRequest(StableId(run_id), initiator)
        )
    )
    return game_to_api(created)


@runs_router.post(
    "/{run_id}/turns",
    response_model=TurnResultModel,
    status_code=status.HTTP_201_CREATED,
    summary="Play one turn in an ACTIVE run",
)
def play_turn(
    run_id: Annotated[UUID, Path()],
    payload: PlayTurnRequestModel,
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    initiator: Annotated[RunInitiator, Depends(get_current_initiator)],
) -> TurnResultModel:
    played = unwrap(
        dependencies.play_turn.apply(
            PlayStoryTurnRequest(StableId(run_id), initiator, payload.player_input)
        )
    )
    return TurnResultModel(
        state=game_state_to_api(played.state),
        proposed_change_count=(
            0 if played.proposed_changes is None else len(played.proposed_changes.changes)
        ),
        summary_failed=played.summary_failure is not None,
        summary_failure_message=(
            None if played.summary_failure is None else played.summary_failure.message
        ),
    )


router.include_router(runs_router)
