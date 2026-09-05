"""Caller identity shared by every run-lifecycle operation."""

from __future__ import annotations

from dataclasses import dataclass


def _required(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{label} darf nicht leer sein")
    return value


@dataclass(frozen=True, slots=True)
class RunInitiator:
    """External identity that owns a proposal, and later the game run."""

    issuer: str
    subject: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "issuer", _required(self.issuer, "Der Issuer"))
        object.__setattr__(self, "subject", _required(self.subject, "Das Subject"))
