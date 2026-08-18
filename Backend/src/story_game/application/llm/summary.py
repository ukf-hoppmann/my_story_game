"""Provider-independent contracts for rolling the story summary forward."""

from __future__ import annotations

from dataclasses import dataclass


def _required(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{label} darf nicht leer sein")
    return value


@dataclass(frozen=True, slots=True)
class StorySummaryRequest:
    """Carry the summary so far plus the turn that has just been completed.

    Only the new turn is passed, not the whole history: the previous summary
    already stands for everything before it, which is what keeps the call cheap
    as a game grows.
    """

    system_prompts: tuple[str, ...]
    player_input: str
    narration: str
    language: str
    previous_summary: str | None = None

    def __post_init__(self) -> None:
        prompts = tuple(prompt.strip() for prompt in self.system_prompts if prompt.strip())
        if not prompts:
            raise ValueError("Mindestens ein Summary-Systemprompt ist erforderlich")
        object.__setattr__(self, "system_prompts", prompts)
        for name, label in (
            ("player_input", "Die Spielereingabe"),
            ("narration", "Die Erzählung"),
            ("language", "Die Sprache"),
        ):
            object.__setattr__(self, name, _required(getattr(self, name), label))
        if self.previous_summary is not None:
            summary = self.previous_summary.strip()
            object.__setattr__(self, "previous_summary", summary or None)


@dataclass(frozen=True, slots=True)
class StorySummaryText:
    """Normalized rolling summary returned by a successful summary call."""

    text: str

    def __post_init__(self) -> None:
        text = self.text.strip()
        if not text:
            raise ValueError("Zusammenfassungen dürfen nicht leer sein")
        object.__setattr__(self, "text", text)


__all__ = ["StorySummaryRequest", "StorySummaryText"]
