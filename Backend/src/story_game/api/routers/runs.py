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
from story_game.api.mappers import game_state_to_api, game_to_api, proposal_to_api
from story_game.api.results import OperationFailed, unwrap
from story_game.api.schemas.runs import (
    CharacterDecisionModel,
    ConfirmRunProposalRequestModel,
    ContinuationModel,
    ItemDecisionModel,
    PlayTurnRequestModel,
    ProposeRunRequestModel,
    RunProposalModel,
    RunSummaryListModel,
    RunSummaryModel,
    TurnResultModel,
    UpdateConfigurationRequestModel,
)
from story_game.api.schemas.state import GameDocument, GameStateModel
from story_game.application import (
    CharacterDecision,
    ConfirmGameRunProposalRequest,
    ControllableCharacterSeed,
    ItemDecision,
    PlayStoryTurnRequest,
    ProposeGameRunRequest,
    RunInitiator,
    StartPlaythroughRequest,
)
from story_game.application.game_state import (
    LoadGameRequest,
    ListPlayableRunsRequest,
    UpdateGameConfigurationRequest,
)
from story_game.domain import GameConfiguration, PromptProfile, StableId, StateRevision


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
    initiator: Annotated[RunInitiator, Depends(get_current_initiator)],
    revision: Annotated[int | None, Query(ge=1)] = None,
) -> GameDocument:
    loaded = unwrap(
        dependencies.operations.load.apply(
            LoadGameRequest(
                StableId(run_id),
                initiator.issuer,
                initiator.subject,
                None if revision is None else StateRevision(revision),
            )
        )
    )
    return game_to_api(loaded)


@runs_router.post(
    "/proposals",
    response_model=RunProposalModel,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a reviewable run proposal; persists nothing",
)
def propose_run(
    payload: ProposeRunRequestModel,
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    initiator: Annotated[RunInitiator, Depends(get_current_initiator)],
) -> RunProposalModel:
    configuration = replace(
        DEFAULT_GAME_CONFIGURATION,
        language=payload.language,
        prompt_profile=PromptProfile(
            genre=payload.prompt_profile.genre,
            tone=payload.prompt_profile.tone,
            prose_style=payload.prompt_profile.prose_style,
            perspective=payload.prompt_profile.perspective,
            pacing=payload.prompt_profile.pacing,
            length=payload.prompt_profile.length,
            control_mode=payload.control_mode,
            player_agency=payload.prompt_profile.player_agency,
            consequence=payload.prompt_profile.consequence,
            challenge=payload.prompt_profile.challenge,
            content_profile=payload.prompt_profile.content_profile,
        ),
    )
    validation_error = dependencies.prompt_profile_validator.validate(configuration)
    if validation_error is not None:
        raise OperationFailed(validation_error)
    controllable_characters = tuple(
        ControllableCharacterSeed(item.name, item.description)
        for item in payload.controllable_characters
    )
    proposed = unwrap(
        dependencies.propose_run.apply(
            ProposeGameRunRequest(
                configuration=configuration,
                initial_prompt=payload.initial_prompt,
                initiator=initiator,
                controllable_characters=controllable_characters,
            )
        )
    )
    return proposal_to_api(proposed)


@runs_router.post(
    "",
    response_model=GameDocument,
    status_code=status.HTTP_201_CREATED,
    summary="Confirm a proposal into a new DRAFT scenario template",
)
def confirm_run(
    payload: ConfirmRunProposalRequestModel,
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    initiator: Annotated[RunInitiator, Depends(get_current_initiator)],
) -> GameDocument:
    created = unwrap(
        dependencies.confirm_proposal.apply(
            ConfirmGameRunProposalRequest(
                proposal_id=StableId(payload.proposal_id),
                run_name=payload.run_name,
                initiator=initiator,
                character_decisions=tuple(
                    _character_decision(item) for item in payload.character_decisions
                ),
                item_decisions=tuple(
                    _item_decision(item) for item in payload.item_decisions
                ),
            )
        )
    )
    return game_to_api(created)


def _character_decision(model: CharacterDecisionModel) -> CharacterDecision:
    return CharacterDecision(StableId(model.entity_id), model.role, model.removed)


def _item_decision(model: ItemDecisionModel) -> ItemDecision:
    return ItemDecision(StableId(model.entity_id), model.removed)


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


@runs_router.patch(
    "/{run_id}/configuration",
    response_model=GameStateModel,
    summary="Replace a run's editable story-profile categories as a new revision",
)
def update_configuration(
    run_id: Annotated[UUID, Path()],
    payload: UpdateConfigurationRequestModel,
    dependencies: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    initiator: Annotated[RunInitiator, Depends(get_current_initiator)],
) -> GameStateModel:
    loaded = unwrap(
        dependencies.operations.load.apply(
            LoadGameRequest(StableId(run_id), initiator.issuer, initiator.subject, None)
        )
    )
    current = loaded.state.configuration
    configuration = GameConfiguration(
        language=payload.language,
        prompt_profile=replace(
            current.prompt_profile,
            genre=payload.prompt_profile.genre,
            tone=payload.prompt_profile.tone,
            prose_style=payload.prompt_profile.prose_style,
            perspective=payload.prompt_profile.perspective,
            pacing=payload.prompt_profile.pacing,
            length=payload.prompt_profile.length,
            player_agency=payload.prompt_profile.player_agency,
            consequence=payload.prompt_profile.consequence,
            challenge=payload.prompt_profile.challenge,
            content_profile=payload.prompt_profile.content_profile,
        ),
        narrative_boundaries=current.narrative_boundaries,
        prompt_package_id=current.prompt_package_id,
        prompt_package_version=current.prompt_package_version,
    )
    # No pre-check here (unlike propose_run): update_configuration.apply()
    # already validates via the same PromptProfileValidator before writing,
    # and there is no expensive downstream call to save by failing earlier.
    updated = unwrap(
        dependencies.operations.update_configuration.apply(
            UpdateGameConfigurationRequest(
                run_id=StableId(run_id),
                base_revision=StateRevision(payload.base_revision),
                configuration=configuration,
            )
        )
    )
    return game_state_to_api(updated)


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
        continuation=ContinuationModel(
            narration=played.state.story.turns[-1].narration,
            options=list(played.continuation_options),
        ),
        proposed_change_count=(
            0 if played.proposed_changes is None else len(played.proposed_changes.changes)
        ),
        summary_failed=played.summary_failure is not None,
        summary_failure_message=(
            None if played.summary_failure is None else played.summary_failure.message
        ),
    )


router.include_router(runs_router)
