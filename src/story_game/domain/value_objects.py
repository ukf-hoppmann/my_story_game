"""Small, persistence-independent domain value objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID, uuid4

from .errors import ValidationError


@dataclass(frozen=True, slots=True)
class StableId:
    """An application-owned identifier used for all persistent domain objects."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ValidationError("Eine stabile ID muss eine UUID sein")

    @classmethod
    def parse(cls, value: UUID | str) -> StableId:
        """Parse a UUID received at a serialization boundary."""
        if isinstance(value, UUID):
            return cls(value)
        try:
            return cls(UUID(value))
        except (AttributeError, TypeError, ValueError) as error:
            raise ValidationError("Eine stabile ID muss eine UUID sein") from error

    @classmethod
    def new(cls) -> StableId:
        """Create an identifier for a new in-memory domain object."""
        return cls(uuid4())

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True, order=True)
class StateRevision:
    """Monotonically increasing revision of the canonical game state."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise ValidationError("Eine State-Revision muss positiv sein")

    def next(self) -> StateRevision:
        return StateRevision(self.value + 1)


@dataclass(frozen=True, slots=True, order=True)
class StorySequence:
    """Monotonically ordered sequence number in the visible story timeline."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise ValidationError("Eine Story-Sequenz muss positiv sein")


class EntityKind(StrEnum):
    """Kinds of world objects supported by the narrative core."""

    CHARACTER = "character"
    LOCATION = "location"
    ITEM = "item"
    CREATURE = "creature"
    FACTION = "faction"


class ActorRole(StrEnum):
    """Narrative role of an entity that can act or possess knowledge."""

    PLAYER = "player"
    NPC = "npc"
    NEUTRAL = "neutral"


class RelationKind(StrEnum):
    """Relationships whose current meaning is part of the canonical world."""

    LOCATED_IN = "located_in"
    POSSESSES = "possesses"
    CONTAINS = "contains"
    MEMBER_OF = "member_of"
    KNOWS = "knows"
    ALLIED_WITH = "allied_with"
    HOSTILE_TO = "hostile_to"
    RELATED_TO = "related_to"


class VisibilityScope(StrEnum):
    """Audience scopes for canonical narrative information."""

    PUBLIC = "public"
    PLAYER_KNOWN = "player_known"
    ACTOR_KNOWN = "actor_known"
    DIRECTOR_ONLY = "director_only"


@dataclass(frozen=True, slots=True)
class Visibility:
    """Visibility with an optional actor-specific audience."""

    scope: VisibilityScope
    actor_id: StableId | None = None

    def __post_init__(self) -> None:
        if self.scope is VisibilityScope.ACTOR_KNOWN and self.actor_id is None:
            raise ValidationError(
                "Akteurspezifische Sichtbarkeit benötigt eine Akteurs-ID"
            )
        if self.scope is not VisibilityScope.ACTOR_KNOWN and self.actor_id is not None:
            raise ValidationError(
                "Eine Akteurs-ID ist nur für akteurspezifische Sichtbarkeit erlaubt"
            )

    @classmethod
    def public(cls) -> Visibility:
        return cls(VisibilityScope.PUBLIC)

    @classmethod
    def player_known(cls) -> Visibility:
        return cls(VisibilityScope.PLAYER_KNOWN)

    @classmethod
    def actor_known(cls, actor_id: StableId) -> Visibility:
        return cls(VisibilityScope.ACTOR_KNOWN, actor_id)

    @classmethod
    def director_only(cls) -> Visibility:
        return cls(VisibilityScope.DIRECTOR_ONLY)


class GameRunStatus(StrEnum):
    """Lifecycle of one playable game run."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class GameRole(StrEnum):
    """Application-owned membership roles for a game run."""

    OWNER = "owner"
    PLAYER = "player"


class GoalKind(StrEnum):
    """Priority of an objective in the structured world state."""

    MAIN = "main"
    SIDE = "side"


class GoalStatus(StrEnum):
    OPEN = "open"
    COMPLETED = "completed"
    FAILED = "failed"
