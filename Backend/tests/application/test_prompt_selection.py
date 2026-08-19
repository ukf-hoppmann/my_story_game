from __future__ import annotations

from pathlib import Path

from story_game.application.llm import (
    ExtractionPromptSelectionResolver,
    InitialExtractionPromptSelectionResolver,
    StoryInitializationPromptResolver,
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


def test_initialization_selection_uses_the_profile_without_story_context() -> None:
    resolver = StoryInitializationPromptResolver(FilePromptPackageCatalog(PROMPT_ROOT))

    selection = resolver.resolve(configuration())

    assert selection.task.id == "story_initialization"
    assert selection.options[0].category_id == "genre"


def test_director_selection_omits_player_agency() -> None:
    resolver = StoryInitializationPromptResolver(FilePromptPackageCatalog(PROMPT_ROOT))
    value = configuration()
    director_configuration = GameConfiguration(
        language=value.language,
        prompt_profile=PromptProfile(
            value.prompt_profile.genre,
            value.prompt_profile.tone,
            value.prompt_profile.prose_style,
            value.prompt_profile.perspective,
            value.prompt_profile.pacing,
            "director",
            value.prompt_profile.player_agency,
            value.prompt_profile.consequence,
            value.prompt_profile.challenge,
            value.prompt_profile.content_profile,
        ),
        narrative_boundaries=value.narrative_boundaries,
        prompt_package_id=value.prompt_package_id,
        prompt_package_version=value.prompt_package_version,
    )

    selection = resolver.resolve(director_configuration)

    assert "player_agency" not in {item.category_id for item in selection.options}


def test_extraction_selection_uses_only_the_combined_extraction_option() -> None:
    resolver = ExtractionPromptSelectionResolver(FilePromptPackageCatalog(PROMPT_ROOT))

    selection = resolver.resolve("story.base", "1")

    assert selection.task.id == "worldstate_extraction"
    assert selection.option.category_id == "extraction"
    assert selection.option.option_id == "combined"
    assert not hasattr(selection, "options")


def test_initial_extraction_selection_uses_its_own_task() -> None:
    resolver = InitialExtractionPromptSelectionResolver(
        FilePromptPackageCatalog(PROMPT_ROOT)
    )

    selection = resolver.resolve("story.base", "1")

    assert selection.task.id == "worldstate_initialization"
    assert "ohne eine von ihnen als Spielerfigur zu markieren" in selection.task.text
    assert "höchstens einmal" in selection.task.text
    assert selection.option.category_id == "extraction"
    assert selection.option.option_id == "combined"
