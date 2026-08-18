"""Provider-independent contracts for the initial structured WorldState call."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.initialization_models import ControllableCharacterSeed
from story_game.domain import EntityKind, RelationKind


def reserved_reference(index: int) -> str:
    """The local reference reserved for the controllable character at ``index``.

    Index 0 keeps the original ``player_character`` string so Player Mode's
    wire contract stays unchanged; Director Mode extends it additively
    (``player_character_2``, ``player_character_3``, ...). Both the
    extraction system prompt and the LM Studio wire schema derive names from
    this single function so they cannot drift apart.
    """
    return "player_character" if index == 0 else f"player_character_{index + 1}"


def _stripped_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


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
    evidence: str | None = None
    """Optional verbatim quote from the prose that justifies this proposal.

    Only turn extraction asks for it; initial extraction leaves it unset,
    because there is no earlier world its output could contradict.
    """

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", _stripped_or_none(self.evidence))
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
    evidence: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", _stripped_or_none(self.evidence))
        object.__setattr__(self, "source_ref", _required(self.source_ref, "Die Quellreferenz"))
        object.__setattr__(self, "target_ref", _required(self.target_ref, "Die Zielreferenz"))
        if self.quantity is not None and self.quantity < 1:
            raise ValueError("Eine Candidate-Menge muss positiv sein")
        object.__setattr__(self, "description", self.description.strip())


@dataclass(frozen=True, slots=True)
class CandidateFact:
    statement: str
    subject_ref: str | None = None
    evidence: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", _stripped_or_none(self.evidence))
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
    scene_refs: tuple[str, ...] = ()
    """Local references to the locations the opening is set in, primary first.

    Separate from the location links: those say where an entity is, this says
    where the narration looks. The Application maps them to stable IDs and
    rejects references that are unknown, duplicated, or not locations.
    """

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "scene_refs",
            tuple(
                _required(reference, "Die Schauplatzreferenz")
                for reference in self.scene_refs
            ),
        )


@dataclass(frozen=True, slots=True)
class InitialWorldExtractionRequest:
    """Prepared initial extraction context without prompt or canonical state."""

    system_prompts: tuple[str, ...]
    opening_narration: str
    language: str
    perspective: str
    control_mode: str
    controllable_characters: tuple[ControllableCharacterSeed, ...] = ()

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
