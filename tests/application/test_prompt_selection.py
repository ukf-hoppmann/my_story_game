from __future__ import annotations

from pathlib import Path

from story_game.application.llm import (
    ExtractionPromptSelectionResolver,
    StoryPromptSelectionResolver,
)
from story_game.domain import GameConfiguration, PromptProfile
from story_game.infrastructure.llm import FilePromptPackageCatalog


PROMPT_ROOT = Path(__file__).resolve().parents[2] / "prompts"


def configuration() -> GameConfiguration:
    return GameConfiguration(
        language="de",
        prompt_profile=PromptProfile(
            genre="dark_fantasy",
            tone="balanced",
            prose_style="balanced",
            perspective="third_person_limited",
            pacing="balanced",
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


def test_story_selection_resolves_all_profile_options_before_the_adapter() -> None:
    resolver = StoryPromptSelectionResolver(FilePromptPackageCatalog(PROMPT_ROOT))

    selection = resolver.resolve(configuration())

    assert selection.task.id == "story_generation"
    assert [item.category_id for item in selection.options] == [
        "genre",
        "tone",
        "prose_style",
        "perspective",
        "pacing",
        "control_mode",
        "player_agency",
        "consequence",
        "challenge",
        "content_profile",
    ]
    assert selection.options[0].description.startswith("Bedrohliche Fantasy")
    assert selection.language == "de"
    assert selection.narrative_boundaries == ("Keine sexualisierte Gewalt",)
    assert selection.boundary_directive.id == "narrative_boundaries"


def test_extraction_selection_uses_only_the_combined_extraction_option() -> None:
    resolver = ExtractionPromptSelectionResolver(FilePromptPackageCatalog(PROMPT_ROOT))

    selection = resolver.resolve("story.base", "1")

    assert selection.task.id == "worldstate_extraction"
    assert selection.option.category_id == "extraction"
    assert selection.option.option_id == "combined"
    assert not hasattr(selection, "options")
