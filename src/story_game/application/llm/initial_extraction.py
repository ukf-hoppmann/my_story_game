"""Provider-independent contracts for the initial structured WorldState call."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.initialization_models import PlayerCharacterSeed
from story_game.domain import EntityKind, RelationKind


def _required(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{label} darf nicht leer sein")
    return value


@dataclass(frozen=True, slots=True)
class CandidateCondition:
    name: str
    description: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required(self.name, "Der Zustandsname"))
        object.__setattr__(self, "description", self.description.strip())


@dataclass(frozen=True, slots=True)
class CandidateEntity:
    local_ref: str
    kind: EntityKind
    label: str
    description: str = ""
    conditions: tuple[CandidateCondition, ...] = ()
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "local_ref", _required(self.local_ref, "Die lokale Referenz"))
        object.__setattr__(self, "label", _required(self.label, "Die Bezeichnung"))
        object.__setattr__(self, "description", self.description.strip())
        aliases = tuple(alias.strip() for alias in self.aliases if alias.strip())
        if len(aliases) != len(set(aliases)):
            raise ValueError("Candidate-Aliase müssen eindeutig sein")
        object.__setattr__(self, "aliases", aliases)


@dataclass(frozen=True, slots=True)
class CandidateLink:
    source_ref: str
    target_ref: str
    kind: RelationKind
    quantity: int | None = None
    description: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_ref", _required(self.source_ref, "Die Quellreferenz"))
        object.__setattr__(self, "target_ref", _required(self.target_ref, "Die Zielreferenz"))
        if self.quantity is not None and self.quantity < 1:
            raise ValueError("Eine Candidate-Menge muss positiv sein")
        object.__setattr__(self, "description", self.description.strip())


@dataclass(frozen=True, slots=True)
class CandidateFact:
    statement: str
    subject_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "statement", _required(self.statement, "Der Fakt"))
        if self.subject_ref is not None:
            object.__setattr__(
                self,
                "subject_ref",
                _required(self.subject_ref, "Die Subjektreferenz"),
            )


@dataclass(frozen=True, slots=True)
class WorldInitializationCandidate:
    entities: tuple[CandidateEntity, ...] = ()
    links: tuple[CandidateLink, ...] = ()
    facts: tuple[CandidateFact, ...] = ()


@dataclass(frozen=True, slots=True)
class InitialWorldExtractionRequest:
    """Prepared initial extraction context without prompt or canonical state."""

    system_prompts: tuple[str, ...]
    opening_narration: str
    language: str
    perspective: str
    control_mode: str
    player_character: PlayerCharacterSeed | None = None

    def __post_init__(self) -> None:
        prompts = tuple(prompt.strip() for prompt in self.system_prompts if prompt.strip())
        if not prompts:
            raise ValueError("Mindestens ein Extraction-Systemprompt ist erforderlich")
        object.__setattr__(self, "system_prompts", prompts)
        for name, label in (
            ("opening_narration", "Die Eröffnungsprosa"),
            ("language", "Die Sprache"),
            ("perspective", "Die Perspektive"),
            ("control_mode", "Der Control Mode"),
        ):
            object.__setattr__(self, name, _required(getattr(self, name), label))
