"""Completed prose turns and the chain of story summary segments."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from .errors import ValidationError
from .value_objects import StableId, StateRevision, StorySequence


def _required(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValidationError(f"{label} darf nicht leer sein")
    return value


@dataclass(frozen=True, slots=True)
class StoryTurn:
    """Immutable player input and narration committed as one completed turn."""

    id: StableId
    sequence: StorySequence
    player_input: str
    narration: str
    based_on_revision: StateRevision
    resulting_revision: StateRevision
    completed_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "player_input", _required(self.player_input, "Die Spielereingabe")
        )
        object.__setattr__(self, "narration", _required(self.narration, "Die Erzählung"))
        if self.resulting_revision != self.based_on_revision.next():
            raise ValidationError("Ein StoryTurn muss genau eine State-Revision erzeugen")
        if self.completed_at.tzinfo is None:
            raise ValidationError("Der Abschlusszeitpunkt benötigt eine Zeitzone")


@dataclass(frozen=True, slots=True)
class StorySummarySegment:
    """One immutable summary paragraph condensing a fixed window of turns.

    Segments are never rewritten or replaced: a new one is appended whenever
    the configured summary interval completes, and the chain of segments in
    order stands for the story so far.
    """

    from_sequence: StorySequence
    through_sequence: StorySequence
    text: str
    based_on_revision: StateRevision

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", _required(self.text, "Die Zusammenfassung"))
        if self.from_sequence.value > self.through_sequence.value:
            raise ValidationError(
                "Ein Zusammenfassungs-Absatz darf nicht vor seinem eigenen Fenster beginnen"
            )


@dataclass(frozen=True, slots=True)
class StoryInitialization:
    """The user premise and normalized opening prose before the first turn."""

    prompt: str
    narration: str
    completed_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "prompt", _required(self.prompt, "Der Initialprompt"))
        object.__setattr__(self, "narration", _required(self.narration, "Die Eröffnung"))
        if self.completed_at.tzinfo is None:
            raise ValidationError("Der Initialisierungszeitpunkt benötigt eine Zeitzone")


@dataclass(frozen=True, slots=True)
class StoryState:
    """Concrete completed story history without structured world facts."""

    turns: tuple[StoryTurn, ...] = ()
    summaries: tuple[StorySummarySegment, ...] = ()
    current_turn_sequence: int = 0
    initialization: StoryInitialization | None = None

    def __post_init__(self) -> None:
        if self.current_turn_sequence < 0:
            raise ValidationError("Die aktuelle Zugnummer darf nicht negativ sein")
        ids = [turn.id for turn in self.turns]
        if len(ids) != len(set(ids)):
            raise ValidationError("StoryTurns müssen eindeutige IDs besitzen")
        sequences = [turn.sequence.value for turn in self.turns]
        if sequences != list(range(1, len(self.turns) + 1)):
            raise ValidationError("StoryTurns müssen lückenlos bei Zug 1 beginnen")
        if self.current_turn_sequence != len(self.turns):
            raise ValidationError("Die aktuelle Zugnummer muss dem letzten StoryTurn entsprechen")
        previous_through = 0
        for segment in self.summaries:
            if segment.from_sequence.value != previous_through + 1:
                raise ValidationError(
                    "Zusammenfassungs-Absätze müssen lückenlos aneinander anschließen"
                )
            if segment.through_sequence.value > self.current_turn_sequence:
                raise ValidationError(
                    "Ein Zusammenfassungs-Absatz darf keine zukünftigen Züge abdecken"
                )
            previous_through = segment.through_sequence.value

    def add_turn(
        self, turn: StoryTurn, new_summary_segment: StorySummarySegment | None
    ) -> StoryState:
        expected_sequence = self.current_turn_sequence + 1
        if turn.sequence.value != expected_sequence:
            raise ValidationError("Ein neuer StoryTurn muss direkt auf den letzten Zug folgen")
        return replace(
            self,
            turns=(*self.turns, turn),
            summaries=(
                self.summaries
                if new_summary_segment is None
                else (*self.summaries, new_summary_segment)
            ),
            current_turn_sequence=expected_sequence,
        )
