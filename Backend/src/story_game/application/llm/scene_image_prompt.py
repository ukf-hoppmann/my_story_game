"""Provider-independent contracts for writing scene-image prompts.

Two task-specific calls share one result shape: the detailed prompt written
from the last turns of the story, and an optional compact rewrite of it for
image models with a short prompt limit (e.g. SDXL derivatives).
"""

from __future__ import annotations

from dataclasses import dataclass

from .summary import SummarizedTurn


def _required(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{label} darf nicht leer sein")
    return value


@dataclass(frozen=True, slots=True)
class SceneImagePromptRequest:
    """The window of turns one scene-image prompt is written from."""

    system_prompts: tuple[str, ...]
    turns: tuple[SummarizedTurn, ...]
    language: str

    def __post_init__(self) -> None:
        prompts = tuple(prompt.strip() for prompt in self.system_prompts if prompt.strip())
        if not prompts:
            raise ValueError("Mindestens ein Bildprompt-Systemprompt ist erforderlich")
        object.__setattr__(self, "system_prompts", prompts)
        if not self.turns:
            raise ValueError("Ein Bildprompt benötigt mindestens einen Zug")
        object.__setattr__(self, "language", _required(self.language, "Die Sprache"))


@dataclass(frozen=True, slots=True)
class CompactImagePromptRequest:
    """A finished detailed image prompt to be shortened for a compact model."""

    system_prompts: tuple[str, ...]
    prompt: str
    max_words: int

    def __post_init__(self) -> None:
        prompts = tuple(prompt.strip() for prompt in self.system_prompts if prompt.strip())
        if not prompts:
            raise ValueError("Mindestens ein Kurzprompt-Systemprompt ist erforderlich")
        object.__setattr__(self, "system_prompts", prompts)
        object.__setattr__(self, "prompt", _required(self.prompt, "Der Bildprompt"))
        if self.max_words < 1:
            raise ValueError("max_words muss positiv sein")


@dataclass(frozen=True, slots=True)
class SceneImagePromptText:
    """Normalized text of one image prompt, never empty."""

    text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", _required(self.text, "Der Bildprompt"))


__all__ = [
    "CompactImagePromptRequest",
    "SceneImagePromptRequest",
    "SceneImagePromptText",
]
