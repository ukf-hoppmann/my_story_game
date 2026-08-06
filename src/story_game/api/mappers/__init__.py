"""Explicit translations between HTTP models and Domain values."""

from .state import game_from_api, game_to_api

__all__ = ["game_from_api", "game_to_api"]
