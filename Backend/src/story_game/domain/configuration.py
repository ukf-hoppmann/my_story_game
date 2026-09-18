"""Per-run configuration persisted with every canonical state revision."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import ValidationError


def _required(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValidationError(f"{label} darf nicht leer sein")
    return value


@dataclass(frozen=True, slots=True)
class PromptProfile:
    """The complete explicit story-prompt selection for one game revision."""

    genre: str
    prose_style: str
    perspective: str
    pacing: str
    control_mode: str
    player_agency: str
    consequence: str
    challenge: str
    content_profile: str
    tone: str | None = None
    length: str = "standard"

    def __post_init__(self) -> None:
        for field_name, label in (
            ("genre", "Das Genre"),
            ("prose_style", "Der Prosa-Stil"),
            ("perspective", "Die Perspektive"),
            ("pacing", "Das Erzähltempo"),
            ("control_mode", "Der Steuerungsmodus"),
            ("player_agency", "Die Spielerautonomie"),
            ("consequence", "Die Konsequenz"),
            ("challenge", "Die Herausforderung"),
            ("content_profile", "Das Inhaltsprofil"),
            ("length", "Die Textlänge"),
        ):
            object.__setattr__(self, field_name, _required(getattr(self, field_name), label))
        if self.tone is not None:
            object.__setattr__(self, "tone", _required(self.tone, "Der Ton"))

    def selections(self) -> tuple[tuple[str, str], ...]:
        """Return the explicit categories in their stable prompt-assembly order.

        `tone` is omitted entirely when unset, so an unspecified tone renders
        no tone text into the prompt and leaves the genre's own implied mood
        undiluted, rather than forcing a neutral default onto every genre.
        """
        tail: tuple[tuple[str, str], ...] = (
            ("prose_style", self.prose_style),
            ("perspective", self.perspective),
            ("pacing", self.pacing),
            ("control_mode", self.control_mode),
            ("player_agency", self.player_agency),
            ("consequence", self.consequence),
            ("challenge", self.challenge),
            ("content_profile", self.content_profile),
            ("length", self.length),
        )
        head: tuple[tuple[str, str], ...] = (("genre", self.genre),)
        if self.tone is not None:
            head += (("tone", self.tone),)
        return head + tail


@dataclass(frozen=True, slots=True)
class GameConfiguration:
    """Fully resolved behavior references required to resume a game unchanged."""

    language: str
    prompt_profile: PromptProfile
    narrative_boundaries: tuple[str, ...]
    prompt_package_id: str
    prompt_package_version: str

    def __post_init__(self) -> None:
        for field_name, label in (
            ("language", "Die Sprache"),
            ("prompt_package_id", "Das Prompt-Paket"),
            ("prompt_package_version", "Die Prompt-Paket-Version"),
        ):
            object.__setattr__(self, field_name, _required(getattr(self, field_name), label))
        boundaries = tuple(
            boundary.strip() for boundary in self.narrative_boundaries if boundary.strip()
        )
        if len(boundaries) != len(set(boundaries)):
            raise ValidationError("Erzählerische Grenzen müssen eindeutig sein")
        object.__setattr__(self, "narrative_boundaries", boundaries)
