"""Transport shapes for the run-lifecycle endpoints (list, init, play)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from story_game.domain import GameRole, GameRunStatus

from story_game.api.default_configuration import DEFAULT_GAME_CONFIGURATION

from .common import APIModel, ControllableCharacterSeedModel, EditablePromptProfileModel
from .state import GameStateModel, WorldStateModel


def _default_editable_prompt_profile() -> EditablePromptProfileModel:
    """Mirror ``DEFAULT_GAME_CONFIGURATION`` so omitting the field is a no-op."""
    profile = DEFAULT_GAME_CONFIGURATION.prompt_profile
    return EditablePromptProfileModel(
        genre=profile.genre,
        tone=profile.tone,
        prose_style=profile.prose_style,
        perspective=profile.perspective,
        pacing=profile.pacing,
        length=profile.length,
        player_agency=profile.player_agency,
        consequence=profile.consequence,
        challenge=profile.challenge,
        content_profile=profile.content_profile,
    )


class ProposeRunRequestModel(APIModel):
    """What a caller supplies to generate one reviewable, unsaved proposal.

    ``language``/``prompt_profile`` default to the server's previous fixed
    values (see ``api/default_configuration.py``) so existing callers that
    omit them keep today's behavior. ``narrative_boundaries`` and the
    prompt-package reference are not caller-editable and always come from
    that same default. No ``run_name`` either — that is only needed once
    the caller confirms the proposal (``ConfirmRunProposalRequestModel``).
    """

    initial_prompt: str = Field(min_length=1)
    control_mode: Literal["player", "director"]
    controllable_characters: list[ControllableCharacterSeedModel] = Field(
        default_factory=list
    )
    language: str = Field(
        default_factory=lambda: DEFAULT_GAME_CONFIGURATION.language, min_length=1
    )
    prompt_profile: EditablePromptProfileModel = Field(
        default_factory=_default_editable_prompt_profile
    )


class ContinuationModel(APIModel):
    """One piece of narration plus the player's suggested next moves.

    Bundles narration prose with its ``options`` so a client always finds
    them together, regardless of where the prose is otherwise nested
    (``TurnResultModel.state``) or would have lived on its own
    (``RunProposalModel``). ``options`` is transient, non-canonical
    presentation data — never persisted as part of ``GameState`` or a
    ``StoryTurn``.
    """

    narration: str = Field(min_length=1)
    options: list[str] = Field(default_factory=list)


class RunProposalModel(APIModel):
    """A not-yet-persisted proposal for the caller to review and edit.

    ``world`` lists every extracted character/item/location as a neutral
    entity — nobody is player-controlled yet. ``suggested_player_entity_ids``
    is a display hint only (which switches to default to "Spieler"), not a
    decision; the caller's actual choice is submitted via
    ``ConfirmRunProposalRequestModel``.
    """

    proposal_id: UUID
    continuation: ContinuationModel
    world: WorldStateModel
    suggested_player_entity_ids: list[UUID] = Field(default_factory=list)
    suggested_title: str = Field(min_length=1)


class CharacterDecisionModel(APIModel):
    entity_id: UUID
    role: Literal["player", "npc"]
    removed: bool = False


class ItemDecisionModel(APIModel):
    entity_id: UUID
    removed: bool = False


class ConfirmRunProposalRequestModel(APIModel):
    """What a caller submits to persist a previously generated proposal.

    ``run_name`` is optional: a blank or omitted value falls back to the
    proposal's model-suggested title (see ``RunProposalModel.suggested_title``).
    """

    proposal_id: UUID
    run_name: str | None = None
    character_decisions: list[CharacterDecisionModel] = Field(default_factory=list)
    item_decisions: list[ItemDecisionModel] = Field(default_factory=list)


class PlayTurnRequestModel(APIModel):
    player_input: str = Field(min_length=1)


class UpdateConfigurationRequestModel(APIModel):
    """Replace a run's editable story-profile categories as a new revision.

    Carries the complete editable profile, not a partial patch — matching
    the underlying ``UpdateGameConfiguration`` operation, which always
    writes a full ``GameConfiguration``. ``control_mode``,
    ``narrative_boundaries`` and the prompt-package reference are not part
    of this request; the server preserves the run's current values for
    those (see ``routers/runs.py::update_configuration``).
    """

    base_revision: int = Field(ge=1)
    language: str = Field(min_length=1)
    prompt_profile: EditablePromptProfileModel


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
    continuation: ContinuationModel
    proposed_change_count: int = Field(ge=0)
    summary_failed: bool
    summary_failure_message: str | None = None
