"""Fixed server-side GameConfiguration used until a config UI exists."""

from __future__ import annotations

from story_game.domain import GameConfiguration, PromptProfile

# No Keycloak, no configuration UI yet: the API applies this one fixed
# configuration for every new run. ``prompt_profile.control_mode`` is
# overridden per request from ``InitializeRunRequestModel.control_mode``
# before use — see ``routers/runs.py``. Mirrors the shape used throughout
# ``tests/application/test_initialize_game_run.py``.
DEFAULT_GAME_CONFIGURATION = GameConfiguration(
    language="de",
    prompt_profile=PromptProfile(
        genre="dark_fantasy",
        tone="balanced",
        prose_style="balanced",
        perspective="third_person_limited",
        pacing="balanced",
        length="standard",
        control_mode="player",
        player_agency="strict",
        consequence="balanced",
        challenge="balanced",
        content_profile="teen",
    ),
    narrative_boundaries=("Keine sexualisierte Gewalt",),
    prompt_package_id="story.base",
    prompt_package_version="1",
)
