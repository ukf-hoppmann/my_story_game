"""Accept a scene-image request: authorize, pick the turn window, store it pending."""

from __future__ import annotations

import random
from collections.abc import Callable
from datetime import datetime, timedelta

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.game_state import LoadGame, LoadGameRequest
from story_game.application.game_state.errors import GameStateOperationError
from story_game.application.llm import SummarizedTurn
from story_game.domain import GameState, StableId

from .errors import SceneImageError, SceneImageErrorKind
from .models import (
    NewSceneImage,
    RequestSceneImageRequest,
    ResolvedSceneImageOptions,
    SceneImageDefaults,
    SceneImageJob,
    SceneImageOptions,
    SceneImageRequested,
)
from .ports import SceneImageStoreError, SceneImageWriter

_MAX_SEED = 2**31 - 1


class RequestSceneImage:
    """Decide what one image is generated from and record it as pending.

    Idempotency is explicit: while an image of the same turn is still pending
    (and not older than ``active_window``, so a crashed server cannot block a
    turn forever), a repeated request returns that image and no new job.
    Nothing here calls a model or the image provider.
    """

    def __init__(
        self,
        load_game: LoadGame,
        writer: SceneImageWriter,
        defaults: SceneImageDefaults,
        new_id: Callable[[], StableId],
        now: Callable[[], datetime],
        active_window: timedelta,
        new_seed: Callable[[], int] = lambda: random.randint(0, _MAX_SEED),
    ) -> None:
        self._load_game = load_game
        self._writer = writer
        self._defaults = defaults
        self._new_id = new_id
        self._now = now
        self._active_window = active_window
        self._new_seed = new_seed

    def apply(
        self, request: RequestSceneImageRequest
    ) -> OperationResult[SceneImageRequested, GameStateOperationError | SceneImageError]:
        options = self._resolve_options(request.options)
        if isinstance(options, Failure):
            return options
        loaded = self._load_game.apply(
            LoadGameRequest(
                request.run_id, request.initiator.issuer, request.initiator.subject
            )
        )
        if isinstance(loaded, Failure):
            return loaded
        window = _turn_window(loaded.data.state, self._defaults.turn_window)
        if window is None:
            return Failure(
                SceneImageError(
                    SceneImageErrorKind.NO_STORY,
                    "Es gibt noch keine Erzählung, aus der ein Bild entstehen könnte.",
                )
            )
        sequence, turns = window
        now = self._now()
        try:
            active = self._writer.find_active(
                request.run_id, sequence, created_after=now - self._active_window
            )
            if active is not None:
                return Success(SceneImageRequested(active, None))
            record = self._writer.create_pending(
                NewSceneImage(
                    self._new_id(), request.run_id, sequence, options.data, now
                )
            )
        except SceneImageStoreError:
            return Failure(
                SceneImageError(
                    SceneImageErrorKind.STORE_UNAVAILABLE,
                    "Das Szenenbild konnte nicht gespeichert werden.",
                )
            )
        return Success(
            SceneImageRequested(
                record,
                SceneImageJob(record, turns, loaded.data.state.configuration),
            )
        )

    def _resolve_options(
        self, options: SceneImageOptions
    ) -> OperationResult[ResolvedSceneImageOptions, SceneImageError]:
        defaults = self._defaults
        model = defaults.model if options.model is None else options.model.strip()
        if options.model is not None and not model:
            return _invalid("Das Bildmodell darf nicht leer sein.")
        refine = defaults.refine if options.refine is None else options.refine
        strength = (
            defaults.refine_strength
            if options.refine_strength is None
            else options.refine_strength
        )
        if not defaults.min_refine_strength <= strength <= defaults.max_refine_strength:
            return _invalid(
                "Die Refine-Stärke muss zwischen "
                f"{defaults.min_refine_strength} und {defaults.max_refine_strength} liegen."
            )
        return Success(
            ResolvedSceneImageOptions(
                model=model,
                refine=refine,
                refine_model=defaults.refine_model,
                refine_strength=strength,
                width=defaults.width,
                height=defaults.height,
                seed=self._new_seed(),
            )
        )


def _invalid(message: str) -> Failure[SceneImageError]:
    return Failure(SceneImageError(SceneImageErrorKind.INVALID_OPTIONS, message))


def _turn_window(
    state: GameState, size: int
) -> tuple[int, tuple[SummarizedTurn, ...]] | None:
    story = state.story
    if story.turns:
        window = story.turns[-size:]
        return story.current_turn_sequence, tuple(
            SummarizedTurn(turn.player_input, turn.narration) for turn in window
        )
    if story.initialization is not None:
        opening = story.initialization
        return 0, (SummarizedTurn(opening.prompt, opening.narration),)
    return None


__all__ = ["RequestSceneImage"]
