"""Canonical state-document codec backed by the JSON mapping implementation."""

from __future__ import annotations

from collections.abc import Mapping

from story_game.domain import GameState

from .mapper import state_from_document, state_to_document


class JsonGameStateDocumentCodec:
    """Adapt the JSON document mapper to the application-owned codec port."""

    def decode(self, document: Mapping[str, object]) -> GameState:
        return state_from_document(document)

    def encode(self, state: GameState) -> dict[str, object]:
        return state_to_document(state)
