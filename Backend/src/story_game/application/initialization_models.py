"""Application values shared by the transient story-initialization stages."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.domain import StoryState, WorldState


@dataclass(frozen=True, slots=True)
class ControllableCharacterSeed:
    """Caller-owned controllable-character identity before a WorldEntity exists."""

    name: str
    description: str = ""

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise ValueError("Der Name der steuerbaren Figur darf nicht leer sein")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", self.description.strip())


@dataclass(frozen=True, slots=True)
class InitializedStory:
    """Complete transient output before GameRun persistence is allowed."""

    story_state: StoryState
    world_state: WorldState
    suggested_title: str = ""
