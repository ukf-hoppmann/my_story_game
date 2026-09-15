"""Provider-independent contracts for producing one summary segment."""

from __future__ import annotations

from dataclasses import dataclass


def _required(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{label} darf nicht leer sein")
    return value


@dataclass(frozen=True, slots=True)
class SummarizedTurn:
    """One raw turn inside the window a summary segment condenses."""

    player_input: str
    narration: str

    def __post_init__(self) -> None:
        for name, label in (
            ("player_input", "Die Spielereingabe"),
            ("narration", "Die Erzählung"),
        ):
            object.__setattr__(self, name, _required(getattr(self, name), label))


@dataclass(frozen=True, slots=True)
class StorySummaryRequest:
    """The exact window of turns one new, self-contained segment condenses.

    Carries only this window — never the previous segments — so each segment
    is produced independently of the others and the call stays bounded by the
    configured interval, not by how long the game has run.
    """

    system_prompts: tuple[str, ...]
    turns: tuple[SummarizedTurn, ...]
    language: str

    def __post_init__(self) -> None:
        prompts = tuple(prompt.strip() for prompt in self.system_prompts if prompt.strip())
        if not prompts:
            raise ValueError("Mindestens ein Summary-Systemprompt ist erforderlich")
        object.__setattr__(self, "system_prompts", prompts)
        if not self.turns:
            raise ValueError("Ein Zusammenfassungsfenster benötigt mindestens einen Zug")
        object.__setattr__(self, "language", _required(self.language, "Die Sprache"))


@dataclass(frozen=True, slots=True)
class StorySummaryText:
    """Normalized text of one newly produced summary segment."""

    text: str

    def __post_init__(self) -> None:
        text = self.text.strip()
        if not text:
            raise ValueError("Zusammenfassungen dürfen nicht leer sein")
        object.__setattr__(self, "text", text)


__all__ = ["StorySummaryRequest", "StorySummaryText", "SummarizedTurn"]
