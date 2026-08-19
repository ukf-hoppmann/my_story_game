"""Transport shapes for the run-lifecycle endpoints (list, init, play)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from story_game.domain import GameRole, GameRunStatus

from .common import APIModel, ControllableCharacterSeedModel
from .state import GameStateModel, WorldStateModel


class ProposeRunRequestModel(APIModel):
    """What a caller supplies to generate one reviewable, unsaved proposal.

    No ``configuration`` field: the API applies one fixed server-side
    ``GameConfiguration`` (see ``api/app.py``), only overriding
    ``control_mode`` from this request — there is no configuration UI yet.
    No ``run_name`` either — that is only needed once the caller confirms
    the proposal (``ConfirmRunProposalRequestModel``).
    """

    initial_prompt: str = Field(min_length=1)
    control_mode: Literal["player", "director"]
    controllable_characters: list[ControllableCharacterSeedModel] = Field(
        default_factory=list
    )


class RunProposalModel(APIModel):
    """A not-yet-persisted proposal for the caller to review and edit.

    ``world`` lists every extracted character/item/location as a neutral
    entity — nobody is player-controlled yet. ``suggested_player_entity_ids``
    is a display hint only (which switches to default to "Spieler"), not a
    decision; the caller's actual choice is submitted via
    ``ConfirmRunProposalRequestModel``.
    """

    proposal_id: UUID
    opening_narration: str = Field(min_length=1)
    world: WorldStateModel
    suggested_player_entity_ids: list[UUID] = Field(default_factory=list)


class CharacterDecisionModel(APIModel):
    entity_id: UUID
    role: Literal["player", "npc"]
    removed: bool = False


class ItemDecisionModel(APIModel):
    entity_id: UUID
    removed: bool = False


class ConfirmRunProposalRequestModel(APIModel):
    """What a caller submits to persist a previously generated proposal."""

    proposal_id: UUID
    run_name: str = Field(min_length=1)
    character_decisions: list[CharacterDecisionModel] = Field(default_factory=list)
    item_decisions: list[ItemDecisionModel] = Field(default_factory=list)


class PlayTurnRequestModel(APIModel):
    player_input: str = Field(min_length=1)


class RunSummaryModel(APIModel):
    id: UUID
    name: str = Field(min_length=1)
    status: GameRunStatus
    current_revision: int = Field(ge=1)
    game_role: GameRole
    updated_at: datetime


class RunSummaryListModel(APIModel):
    runs: list[RunSummaryModel] = Field(default_factory=list)


class TurnResultModel(APIModel):
    """The committed state plus transient, non-persisted turn diagnostics.

    ``proposed_change_count``/``summary_failed`` deliberately summarize the
    model's untrusted proposal rather than exposing every
    ``ProposedChange`` operation as its own typed schema variant — this data
    is diagnostic ("what did the model want and why"), not something a UI
    needs to act on structurally today, since the canonical result is
    already fully present in ``state``.
    """

    state: GameStateModel
    proposed_change_count: int = Field(ge=0)
    summary_failed: bool
    summary_failure_message: str | None = None
