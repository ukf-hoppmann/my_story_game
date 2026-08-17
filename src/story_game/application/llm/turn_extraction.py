"""Provider-independent contracts for the structured turn-extraction call.

Unlike the initial extraction this call compares new prose against a world that
already exists. Existing objects are therefore addressed through short handles
that the extraction projection hands out for one turn, while genuinely new
objects use local references exactly as the initial extraction does. Neither
form is a stable ID: the Application resolves both, and only after successful
validation does anything receive one.
"""

from __future__ import annotations

from dataclasses import dataclass

from .initial_extraction import (
    CandidateCondition,
    CandidateEntity,
    CandidateFact,
    CandidateLink,
)


def _required(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{label} darf nicht leer sein")
    return value


def _required_all(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    return tuple(_required(value, label) for value in values)


@dataclass(frozen=True, slots=True)
class CandidateEntityUpdate:
    """A change to an entity that already exists.

    Kind and label stay out on purpose: the domain forbids changing an entity's
    kind, and a rename would make the entity unrecognisable across turns.
    """

    handle: str
    description: str | None = None
    conditions: tuple[CandidateCondition, ...] | None = None
    aliases: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "handle", _required(self.handle, "Das Handle"))
        if self.description is not None:
            object.__setattr__(self, "description", self.description.strip())
        if self.aliases is not None:
            aliases = tuple(alias.strip() for alias in self.aliases if alias.strip())
            if len(aliases) != len(set(aliases)):
                raise ValueError("Aliase einer Entität müssen eindeutig sein")
            object.__setattr__(self, "aliases", aliases)


@dataclass(frozen=True, slots=True)
class TurnChangeCandidate:
    """One untrusted delta proposed for a single turn.

    Carries only handles and local references, never stable IDs and never
    approved operations.
    """

    new_entities: tuple[CandidateEntity, ...] = ()
    entity_updates: tuple[CandidateEntityUpdate, ...] = ()
    added_links: tuple[CandidateLink, ...] = ()
    removed_link_handles: tuple[str, ...] = ()
    added_facts: tuple[CandidateFact, ...] = ()
    removed_fact_handles: tuple[str, ...] = ()
    scene_refs: tuple[str, ...] = ()
    """Where the narration looks after this turn, most relevant first."""

    def __post_init__(self) -> None:
        for name, label in (
            ("removed_link_handles", "Ein Beziehungs-Handle"),
            ("removed_fact_handles", "Ein Fakten-Handle"),
            ("scene_refs", "Eine Schauplatzreferenz"),
        ):
            object.__setattr__(self, name, _required_all(getattr(self, name), label))


@dataclass(frozen=True, slots=True)
class TurnExtractionRequest:
    """Prepared comparison request: what happened, against what already holds."""

    system_prompts: tuple[str, ...]
    narration: str
    world_state: str
    language: str

    def __post_init__(self) -> None:
        prompts = tuple(prompt.strip() for prompt in self.system_prompts if prompt.strip())
        if not prompts:
            raise ValueError("Mindestens ein Extraction-Systemprompt ist erforderlich")
        object.__setattr__(self, "system_prompts", prompts)
        for name, label in (
            ("narration", "Die Erzählung"),
            ("world_state", "Der Weltausschnitt"),
            ("language", "Die Sprache"),
        ):
            object.__setattr__(self, name, _required(getattr(self, name), label))


__all__ = [
    "CandidateEntityUpdate",
    "TurnChangeCandidate",
    "TurnExtractionRequest",
]
