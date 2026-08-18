"""Transport shapes for the run-lifecycle endpoints (list, init, play)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from story_game.domain import GameRole, GameRunStatus

from .common import APIModel, PlayerCharacterSeedModel
from .state import GameStateModel


class InitializeRunRequestModel(APIModel):
    """What a caller supplies to start a new DRAFT scenario template.

    No ``configuration`` field: the API applies one fixed server-side
    ``GameConfiguration`` (see ``api/app.py``), only overriding
    ``control_mode`` from this request — there is no configuration UI yet.
    """

    run_name: str = Field(min_length=1)
    initial_prompt: str = Field(min_length=1)
    control_mode: Literal["player", "director"]
    player_character: PlayerCharacterSeedModel | None = None


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
