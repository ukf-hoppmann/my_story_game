"""Find which known world entities the current text actually names."""

from __future__ import annotations

import re
from dataclasses import dataclass

from story_game.application.contracts import OperationResult, Success
from story_game.application.story_turn_context_errors import ContextSelectionError
from story_game.application.story_turn_context_models import (
    EntityCandidate,
    SelectionPriority,
    merge_candidates,
)
from story_game.domain import WorldState


_GERMAN_ENDINGS = ("es", "en", "s", "n")
"""Genitive and plural endings a German name may carry in running text.

Deliberately a short closed list: it lets ``Marens Schwert`` match ``Maren``
while a whole-word match still keeps ``kann`` from matching ``Ann``. Fuzzy or
similarity matching is out of scope because it stops being explainable.
"""

_GERMAN_ARTICLES = frozenset(
    {
        "der",
        "die",
        "das",
        "den",
        "dem",
        "des",
        "ein",
        "eine",
        "einen",
        "einem",
        "einer",
        "eines",
    }
)
"""Leading articles dropped from a name before matching.

German articles decline, so a stored alias like ``der Wirt`` would never match
``den Wirt`` in running text. Matching the noun alone covers every case at once
instead of enumerating declensions.
"""


@dataclass(frozen=True, slots=True)
class ResolveMentionedEntitiesRequest:
    world: WorldState
    player_input: str
    latest_prose: str


class ResolveMentionedEntities:
    """Match labels and aliases as whole words, never guessing on ambiguity."""

    def apply(
        self, request: ResolveMentionedEntitiesRequest
    ) -> OperationResult[tuple[EntityCandidate, ...], ContextSelectionError]:
        from_input = _matches(
            request.world,
            request.player_input,
            SelectionPriority.PLAYER_INPUT,
            "Spielereingabe",
        )
        from_prose = _matches(
            request.world,
            request.latest_prose,
            SelectionPriority.RECENT_PROSE,
            "jüngste Erzählung",
        )
        return Success(merge_candidates(from_input, from_prose))


def _matches(
    world: WorldState,
    text: str,
    priority: SelectionPriority,
    source: str,
) -> tuple[EntityCandidate, ...]:
    if not text.strip():
        return ()
    found: list[EntityCandidate] = []
    for entity in world.entities:
        for name in (entity.label, *entity.aliases):
            if _mentions(text, name):
                found.append(
                    EntityCandidate(
                        entity.id,
                        priority,
                        f"{source}: {name!r}",
                    )
                )
                break
    return tuple(found)


def _mentions(text: str, name: str) -> bool:
    name = _without_leading_article(name)
    if not name:
        return False
    pattern = re.escape(name) + "(?:" + "|".join(_GERMAN_ENDINGS) + ")?"
    return re.search(rf"(?<!\w){pattern}(?!\w)", text, re.IGNORECASE) is not None


def _without_leading_article(name: str) -> str:
    words = name.strip().split()
    if len(words) > 1 and words[0].casefold() in _GERMAN_ARTICLES:
        return " ".join(words[1:])
    return " ".join(words)
