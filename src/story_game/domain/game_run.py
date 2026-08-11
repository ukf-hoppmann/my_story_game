"""Run metadata and external identity memberships."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .errors import ValidationError
from .value_objects import GameRole, GameRunStatus, StableId, StateRevision


def _required(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValidationError(f"{label} darf nicht leer sein")
    return value


@dataclass(frozen=True, slots=True)
class GameRunMember:
    """Stable Keycloak identity membership without local credentials."""

    issuer: str
    subject: str
    game_role: GameRole
    player_entity_id: StableId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "issuer", _required(self.issuer, "Der Issuer"))
        object.__setattr__(self, "subject", _required(self.subject, "Das Subject"))

    @property
    def identity(self) -> tuple[str, str]:
        return self.issuer, self.subject


@dataclass(frozen=True, slots=True)
class GameRun:
    """One game stream with memberships and a pointer to its committed head."""

    id: StableId
    name: str
    status: GameRunStatus
    current_revision: StateRevision
    members: tuple[GameRunMember, ...]
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required(self.name, "Der Name"))
        identities = [member.identity for member in self.members]
        if len(identities) != len(set(identities)):
            raise ValidationError("Mitgliedschaften eines GameRuns müssen eindeutig sein")
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValidationError("GameRun-Zeitpunkte müssen eine Zeitzone besitzen")
        if self.updated_at < self.created_at:
            raise ValidationError("Ein GameRun kann nicht vor seiner Erstellung geändert werden")
