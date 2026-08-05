"""Translate the versioned state document at the HTTP boundary."""

from __future__ import annotations

from story_game.domain import GameState
from story_game.infrastructure.persistence.json.mapper import (
    state_from_document,
    state_to_document,
)

from story_game.api.schemas.state import StateDocument


def state_from_api(document: StateDocument) -> GameState:
    """Validate the transport document again through the canonical domain mapper."""
    return state_from_document(document.model_dump(mode="json"))


def state_to_api(state: GameState) -> StateDocument:
    """Expose a domain state through the documented transport shape."""
    return StateDocument.model_validate(state_to_document(state))
