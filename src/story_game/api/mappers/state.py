"""Translate the versioned state document at the HTTP boundary."""

from __future__ import annotations

from story_game.application.ports import GameStateDocumentCodec
from story_game.domain import GameState

from story_game.api.schemas.state import StateDocument


def state_from_api(
    document: StateDocument, codec: GameStateDocumentCodec
) -> GameState:
    """Translate the validated HTTP document through the configured codec port."""
    return codec.decode(document.model_dump(mode="json"))


def state_to_api(state: GameState, codec: GameStateDocumentCodec) -> StateDocument:
    """Expose a domain state through the documented transport shape."""
    return StateDocument.model_validate(codec.encode(state))
