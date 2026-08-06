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
class GameConfiguration:
    """Fully resolved behavior references required to resume a game unchanged."""

    language: str
    narration_style_id: str
    perspective_id: str
    control_mode_id: str
    narrative_boundaries: tuple[str, ...]
    story_model_id: str
    extraction_model_id: str
    summary_model_id: str
    prompt_package_id: str
    prompt_package_version: str

    def __post_init__(self) -> None:
        for field_name, label in (
            ("language", "Die Sprache"),
            ("narration_style_id", "Der Erzählstil"),
            ("perspective_id", "Die Perspektive"),
            ("control_mode_id", "Der Steuerungsmodus"),
            ("story_model_id", "Das Story-Modell"),
            ("extraction_model_id", "Das Extraktionsmodell"),
            ("summary_model_id", "Das Zusammenfassungsmodell"),
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
