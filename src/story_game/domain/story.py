"""Canonical chronological and dramaturgical story-state entities."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .errors import InvalidReferenceError, ValidationError
from .value_objects import (
    ChapterStatus,
    GoalStatus,
    StableId,
    StateRevision,
    StorySequence,
    ThreadStatus,
    Visibility,
)


def _text(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValidationError(f"{label} darf nicht leer sein")
    return value


def _unique_ids(items: tuple[object, ...], label: str) -> None:
    ids = [getattr(item, "id", None) for item in items]
    if len(ids) != len(set(ids)):
        raise ValidationError(f"{label} müssen eindeutige IDs besitzen")


@dataclass(frozen=True, slots=True)
class StoryEvent:
    """An accepted, ordered event in the story chronology."""

    id: StableId
    sequence: StorySequence
    kind: str
    description: str
    participant_ids: tuple[StableId, ...] = ()
    visibility: Visibility = field(default_factory=Visibility.public)

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _text(self.kind, "Der Ereignistyp"))
        object.__setattr__(
            self, "description", _text(self.description, "Die Ereignisbeschreibung")
        )
        if len(self.participant_ids) != len(set(self.participant_ids)):
            raise ValidationError("Ereignisteilnehmer müssen eindeutig sein")


@dataclass(frozen=True, slots=True)
class SceneParticipant:
    """A role-bearing, current participant in a scene."""

    entity_id: StableId
    role: str
    visibility: Visibility = field(default_factory=Visibility.public)

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", _text(self.role, "Die Szenenrolle"))


@dataclass(frozen=True, slots=True)
class Scene:
    """A concrete scene identity and its current visible cast."""

    id: StableId
    sequence: StorySequence
    location_id: StableId
    participants: tuple[SceneParticipant, ...] = ()
    title: str = ""
    focus: str = ""
    focus_entity_id: StableId | None = None

    def __post_init__(self) -> None:
        participant_ids = [participant.entity_id for participant in self.participants]
        if len(participant_ids) != len(set(participant_ids)):
            raise ValidationError("Szenenteilnehmer müssen eindeutig sein")
        object.__setattr__(self, "title", self.title.strip())
        object.__setattr__(self, "focus", self.focus.strip())


@dataclass(frozen=True, slots=True)
class Chapter:
    """A dramaturgical chapter in the story state."""

    id: StableId
    sequence: int
    title: str
    status: ChapterStatus = ChapterStatus.PLANNED
    summary: str = ""

    def __post_init__(self) -> None:
        if self.sequence < 1:
            raise ValidationError("Eine Kapitelreihenfolge muss positiv sein")
        object.__setattr__(self, "title", _text(self.title, "Der Kapiteltitel"))
        object.__setattr__(self, "summary", self.summary.strip())


@dataclass(frozen=True, slots=True)
class StoryThread:
    """An unresolved or resolved narrative thread."""

    id: StableId
    title: str
    status: ThreadStatus = ThreadStatus.OPEN
    progress: int = 0
    related_entity_ids: tuple[StableId, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", _text(self.title, "Der Threadtitel"))
        if not 0 <= self.progress <= 100:
            raise ValidationError("Thread-Fortschritt muss zwischen 0 und 100 liegen")
        if len(self.related_entity_ids) != len(set(self.related_entity_ids)):
            raise ValidationError("Thread-Referenzen müssen eindeutig sein")


@dataclass(frozen=True, slots=True)
class Goal:
    """A concrete objective belonging to an actor or the story."""

    id: StableId
    title: str
    owner_id: StableId | None = None
    status: GoalStatus = GoalStatus.OPEN
    progress: int = 0
    related_entity_ids: tuple[StableId, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", _text(self.title, "Der Zieltitel"))
        if not 0 <= self.progress <= 100:
            raise ValidationError("Ziel-Fortschritt muss zwischen 0 und 100 liegen")
        if len(self.related_entity_ids) != len(set(self.related_entity_ids)):
            raise ValidationError("Zielreferenzen müssen eindeutig sein")


@dataclass(frozen=True, slots=True)
class StorySummary:
    """Derived memory for an explicitly covered story sequence range."""

    from_sequence: StorySequence
    through_sequence: StorySequence
    text: str
    based_on_revision: StateRevision

    def __post_init__(self) -> None:
        if self.through_sequence < self.from_sequence:
            raise ValidationError(
                "Eine Zusammenfassung muss einen gültigen Sequenzbereich abdecken"
            )
        object.__setattr__(self, "text", _text(self.text, "Die Zusammenfassung"))


@dataclass(frozen=True, slots=True)
class StoryState:
    """Chronology, current scene and dramaturgical progress."""

    events: tuple[StoryEvent, ...] = ()
    scenes: tuple[Scene, ...] = ()
    chapters: tuple[Chapter, ...] = ()
    threads: tuple[StoryThread, ...] = ()
    goals: tuple[Goal, ...] = ()
    summaries: tuple[StorySummary, ...] = ()
    current_scene_id: StableId | None = None
    current_chapter_id: StableId | None = None
    current_sequence: int = 0

    def __post_init__(self) -> None:
        _unique_ids(self.events, "Ereignisse")
        _unique_ids(self.scenes, "Szenen")
        _unique_ids(self.chapters, "Kapitel")
        _unique_ids(self.threads, "Threads")
        _unique_ids(self.goals, "Ziele")
        if self.current_sequence < 0:
            raise ValidationError("Die aktuelle Story-Sequenz darf nicht negativ sein")
        event_sequences = [event.sequence.value for event in self.events]
        if event_sequences != sorted(event_sequences):
            raise ValidationError("Ereignisse müssen chronologisch sortiert sein")
        if event_sequences and event_sequences[-1] > self.current_sequence:
            raise ValidationError(
                "Die aktuelle Sequenz darf nicht hinter einem Ereignis liegen"
            )
        if self.current_scene_id is not None and not any(
            scene.id == self.current_scene_id for scene in self.scenes
        ):
            raise InvalidReferenceError("Die aktuelle Szene ist unbekannt")
        if self.current_chapter_id is not None and not any(
            chapter.id == self.current_chapter_id for chapter in self.chapters
        ):
            raise InvalidReferenceError("Das aktuelle Kapitel ist unbekannt")

    def add_event(self, event: StoryEvent) -> StoryState:
        if any(existing.id == event.id for existing in self.events):
            raise ValidationError(f"Die Ereignis-ID existiert bereits: {event.id}")
        if self.events and event.sequence <= self.events[-1].sequence:
            raise ValidationError("Ein neues Ereignis muss chronologisch folgen")
        return replace(
            self,
            events=(*self.events, event),
            current_sequence=max(self.current_sequence, event.sequence.value),
        )

    def add_scene(self, scene: Scene) -> StoryState:
        if any(existing.id == scene.id for existing in self.scenes):
            raise ValidationError(f"Die Szenen-ID existiert bereits: {scene.id}")
        return replace(self, scenes=(*self.scenes, scene))

    def set_current_scene(self, scene_id: StableId) -> StoryState:
        if not any(scene.id == scene_id for scene in self.scenes):
            raise InvalidReferenceError(f"Unbekannte Szene: {scene_id}")
        return replace(self, current_scene_id=scene_id)

    def add_chapter(self, chapter: Chapter) -> StoryState:
        if any(existing.id == chapter.id for existing in self.chapters):
            raise ValidationError(f"Die Kapitel-ID existiert bereits: {chapter.id}")
        return replace(self, chapters=(*self.chapters, chapter))

    def add_thread(self, thread: StoryThread) -> StoryState:
        if any(existing.id == thread.id for existing in self.threads):
            raise ValidationError(f"Die Thread-ID existiert bereits: {thread.id}")
        return replace(self, threads=(*self.threads, thread))

    def update_thread(self, thread: StoryThread) -> StoryState:
        if not any(existing.id == thread.id for existing in self.threads):
            raise InvalidReferenceError(f"Unbekannter Thread: {thread.id}")
        return replace(
            self,
            threads=tuple(
                thread if existing.id == thread.id else existing
                for existing in self.threads
            ),
        )

    def add_goal(self, goal: Goal) -> StoryState:
        if any(existing.id == goal.id for existing in self.goals):
            raise ValidationError(f"Die Ziel-ID existiert bereits: {goal.id}")
        return replace(self, goals=(*self.goals, goal))

    def update_goal(self, goal: Goal) -> StoryState:
        if not any(existing.id == goal.id for existing in self.goals):
            raise InvalidReferenceError(f"Unbekanntes Ziel: {goal.id}")
        return replace(
            self,
            goals=tuple(
                goal if existing.id == goal.id else existing for existing in self.goals
            ),
        )
