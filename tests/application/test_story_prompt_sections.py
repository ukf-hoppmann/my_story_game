from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from story_game.application import Success
from story_game.application.llm import StoryPromptSelectionResolver
from story_game.application.story_prompt_sections import (
    configuration_text,
    extraction_projection,
    story_state_text,
    world_state_text,
)
from story_game.application.story_turn_context import (
    SelectStoryTurnContextRequest,
    build_story_turn_context_selection,
)
from story_game.infrastructure.llm import FilePromptPackageCatalog
from tests.application import turn_context_world as w


PROMPT_ROOT = Path(__file__).parents[2] / "prompts"


def selection():
    return StoryPromptSelectionResolver(FilePromptPackageCatalog(PROMPT_ROOT)).resolve(
        w.configuration()
    )


def context(player_input: str = "Ich frage den Wirt.", *narrations: str):
    state = w.game_state((w.TAVERN,), *narrations)
    result = build_story_turn_context_selection().apply(
        SelectStoryTurnContextRequest(state, w.MAREN, player_input)
    )
    assert isinstance(result, Success), result
    return result.data


def test_configuration_text_resolves_option_ids_into_readable_instructions() -> None:
    text = configuration_text(selection())

    assert "Sprache: de" in text
    assert "Erzählerische Grenzen: Keine sexualisierte Gewalt" in text
    # The stored profile holds option IDs; only their descriptions may reach the
    # model, because the adapter must not interpret IDs itself.
    assert "dark_fantasy" not in text
    assert "second_person" not in text
    assert "Bedrohliche Fantasy" in text


def test_configuration_text_covers_every_resolved_category() -> None:
    resolved = selection()

    text = configuration_text(resolved)

    for option in resolved.options:
        assert option.description in text


def test_world_state_text_carries_the_selected_world() -> None:
    text = world_state_text(context())

    assert "Wirtshaus" in text
    assert "Bertram" in text
    assert "Silber verletzt Geister." in text
    assert "Finde den Geheimgang" in text


def test_world_state_text_names_the_scene() -> None:
    text = world_state_text(context())

    assert "Wirtshaus" in text.split("[entities]")[0]


def test_hidden_facts_appear_without_any_special_marking() -> None:
    """First cut deliberately does not mark visibility; see TASK-018."""
    text = world_state_text(context())

    assert "Bertram wird die Gruppe verraten." in text
    assert "director_only" not in text


def test_an_empty_selection_yields_a_readable_placeholder() -> None:
    empty = replace(
        context(),
        scene_locations=(),
        entities=(),
        links=(),
        facts=(),
        knowledge=(),
        rules=(),
        goals=(),
        controlled_entity=None,
    )

    text = world_state_text(empty)

    assert text.strip() != ""
    assert "keine" in text.casefold()


def test_story_state_text_carries_summary_and_recent_turns_in_order() -> None:
    text = story_state_text(context("Ich warte.", "Erster Zug.", "Zweiter Zug."))

    assert "Maren hat das Wirtshaus erreicht." in text
    assert text.index("Erster Zug.") < text.index("Zweiter Zug.")


def test_story_state_text_stays_readable_before_the_first_turn() -> None:
    text = story_state_text(context("Ich sehe mich um."))

    assert text.strip() != ""


def test_the_extraction_projection_hands_out_a_handle_per_object() -> None:
    selected = context()

    projection = extraction_projection(selected)

    assert set(projection.entity_handles.values()) == {
        entity.id for entity in selected.entities
    }
    assert set(projection.link_handles.values()) == {
        link.id for link in selected.links
    }
    assert set(projection.fact_handles.values()) == {
        fact.id for fact in selected.facts
    }


def test_every_handle_appears_in_the_rendered_text() -> None:
    projection = extraction_projection(context())

    for handle in projection.entity_handles:
        assert handle in projection.text


def test_handles_are_short_and_never_a_stable_id() -> None:
    """Long identifiers cost tokens and local models mistype them."""
    selected = context()

    projection = extraction_projection(selected)

    assert all(len(handle) <= 6 for handle in projection.entity_handles)
    for entity in selected.entities:
        assert str(entity.id) not in projection.text


def test_the_projection_is_deterministic() -> None:
    selected = context()

    assert extraction_projection(selected) == extraction_projection(selected)


def test_handles_of_different_object_kinds_do_not_collide() -> None:
    projection = extraction_projection(context())

    handles = (
        set(projection.entity_handles)
        | set(projection.link_handles)
        | set(projection.fact_handles)
    )
    assert len(handles) == (
        len(projection.entity_handles)
        + len(projection.link_handles)
        + len(projection.fact_handles)
    )


def test_the_projection_survives_an_empty_selection() -> None:
    empty = replace(
        context(),
        scene_locations=(),
        entities=(),
        links=(),
        facts=(),
        knowledge=(),
        rules=(),
        goals=(),
        controlled_entity=None,
    )

    projection = extraction_projection(empty)

    assert projection.entity_handles == {}
    assert projection.text.strip() != ""
