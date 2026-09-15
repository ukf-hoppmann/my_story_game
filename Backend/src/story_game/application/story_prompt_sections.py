"""Render prepared application meaning into the model's text sections.

The stored `PromptProfile` holds option IDs such as ``dark_fantasy``. Only their
resolved descriptions may reach a model, because a provider adapter must not
interpret the project's own option IDs. These functions turn already resolved
application values into the plain text the model request carries.

They are plain functions on purpose: no collaborators, no failure modes, and no
step a workflow delegates to in a visible order.
"""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.llm import StoryPromptSelection
from story_game.application.story_turn_context_models import SelectedStoryTurnContext
from story_game.domain import (
    EntityLink,
    Fact,
    Goal,
    KnowledgeEntry,
    StableId,
    WorldEntity,
    WorldRule,
)


_NO_WORLD_DATA = "Es sind noch keine relevanten Weltdaten bekannt."
"""Stands in for an empty selection.

Director control may legitimately reach a turn with nothing selected, while the
model request rejects empty text. Saying so plainly beats failing the turn.
"""

_NO_STORY_YET = "Es gibt noch keine erzählte Vorgeschichte."


def configuration_text(selection: StoryPromptSelection) -> str:
    """Render resolved prompt meaning without exposing option IDs to the adapter."""
    return "\n".join(
        (
            f"Sprache: {selection.language}",
            *(f"{item.category_id}: {item.description}" for item in selection.options),
            "Erzählerische Grenzen: " + "; ".join(selection.narrative_boundaries),
        )
    )


def world_state_text(context: SelectedStoryTurnContext) -> str:
    """Render the selected world slice as named sections.

    Visibility is deliberately not shown. The slice contains hidden facts so the
    model can steer towards them, and how it may use them is a prompting
    question that is still open.
    """
    labels = {entity.id: entity.label for entity in context.entities}
    sections = (
        ("scene", tuple(_entity_line(item) for item in context.scene_locations)),
        ("entities", tuple(_entity_line(item) for item in context.entities)),
        ("relations", tuple(_link_line(item, labels) for item in context.links)),
        ("facts", tuple(_fact_line(item, labels) for item in context.facts)),
        ("knowledge", tuple(_knowledge_line(item, labels) for item in context.knowledge)),
        ("rules", tuple(_rule_line(item) for item in context.rules)),
        ("goals", tuple(_goal_line(item) for item in context.goals)),
    )
    rendered = tuple(
        _section(name, lines) for name, lines in sections if lines
    )
    return "\n\n".join(rendered) if rendered else _NO_WORLD_DATA


def story_state_text(context: SelectedStoryTurnContext) -> str:
    """Render the summary segment chain and the most recent turns, in order."""
    parts: list[str] = []
    if context.summaries:
        parts.append(
            _section("summary", tuple(segment.text for segment in context.summaries))
        )
    turns = tuple(
        f"Zug {turn.sequence.value}\n"
        f"Spieler: {turn.player_input}\n"
        f"Erzählung: {turn.narration}"
        for turn in context.recent_turns
    )
    if turns:
        parts.append(_section("recent_turns", turns))
    return "\n\n".join(parts) if parts else _NO_STORY_YET


@dataclass(frozen=True, slots=True)
class TurnExtractionProjection:
    """The comparison text plus the handles it hands out for this one turn.

    Extraction has to address existing objects unambiguously, which the story
    projection cannot do: it shows labels only, and equally named entities are
    allowed. Short handles beat stable IDs here because they cost far fewer
    tokens and a local model mistyping one long identifier would otherwise
    discard the whole turn.
    """

    text: str
    entity_handles: dict[str, StableId]
    link_handles: dict[str, StableId]
    fact_handles: dict[str, StableId]


def extraction_projection(
    context: SelectedStoryTurnContext,
) -> TurnExtractionProjection:
    """Render the current world slice with a handle on every addressable object."""
    entity_handles = {f"e{index}": item.id for index, item in enumerate(context.entities, 1)}
    link_handles = {f"l{index}": item.id for index, item in enumerate(context.links, 1)}
    fact_handles = {f"f{index}": item.id for index, item in enumerate(context.facts, 1)}
    labels = {item.id: item.label for item in context.entities}
    by_id = {value: key for key, value in entity_handles.items()}

    scene = tuple(
        f"{by_id[item.id]} {item.label}"
        for item in context.scene_locations
        if item.id in by_id
    )
    entities = tuple(
        f"{handle} {_entity_line(_entity(context, entity_id))}"
        for handle, entity_id in entity_handles.items()
    )
    links = tuple(
        f"{handle} {_link_line(_link(context, link_id), labels)}"
        for handle, link_id in link_handles.items()
    )
    facts = tuple(
        f"{handle} {_fact_line(_fact(context, fact_id), labels)}"
        for handle, fact_id in fact_handles.items()
    )
    sections = tuple(
        _section(name, lines)
        for name, lines in (
            ("scene", scene),
            ("entities", entities),
            ("relations", links),
            ("facts", facts),
        )
        if lines
    )
    return TurnExtractionProjection(
        text="\n\n".join(sections) if sections else _NO_WORLD_DATA,
        entity_handles=entity_handles,
        link_handles=link_handles,
        fact_handles=fact_handles,
    )


def _entity(context: SelectedStoryTurnContext, entity_id: StableId) -> WorldEntity:
    return next(item for item in context.entities if item.id == entity_id)


def _link(context: SelectedStoryTurnContext, link_id: StableId) -> EntityLink:
    return next(item for item in context.links if item.id == link_id)


def _fact(context: SelectedStoryTurnContext, fact_id: StableId) -> Fact:
    return next(item for item in context.facts if item.id == fact_id)


def _section(name: str, lines: tuple[str, ...]) -> str:
    return f"[{name}]\n" + "\n".join(lines)


def _entity_line(entity: WorldEntity) -> str:
    parts = [f"{entity.label} ({entity.kind.value})"]
    if entity.actor is not None:
        parts.append(f"Rolle: {entity.actor.role.value}")
    if entity.aliases:
        parts.append("auch genannt: " + ", ".join(entity.aliases))
    if entity.description:
        parts.append(entity.description)
    if entity.conditions:
        parts.append(
            "Zustand: " + ", ".join(condition.name for condition in entity.conditions)
        )
    return " — ".join(parts)


def _link_line(link: EntityLink, labels: dict[StableId, str]) -> str:
    line = (
        f"{_label(link.source_id, labels)} {link.kind.value} "
        f"{_label(link.target_id, labels)}"
    )
    if link.quantity is not None:
        line += f" (Menge: {link.quantity})"
    if link.description:
        line += f" — {link.description}"
    return line


def _fact_line(fact: Fact, labels: dict[StableId, str]) -> str:
    if fact.subject_id is None:
        return fact.statement
    return f"{_label(fact.subject_id, labels)}: {fact.statement}"


def _knowledge_line(entry: KnowledgeEntry, labels: dict[StableId, str]) -> str:
    return (
        f"{_label(entry.actor_id, labels)} weiß seit Zug "
        f"{entry.learned_at.value} von einer der genannten Tatsachen"
    )


def _rule_line(rule: WorldRule) -> str:
    return rule.statement


def _goal_line(goal: Goal) -> str:
    return f"{goal.title} ({goal.kind.value}, {goal.status.value}) — {goal.description}"


def _label(entity_id: StableId, labels: dict[StableId, str]) -> str:
    return labels.get(entity_id, str(entity_id))


__all__ = [
    "TurnExtractionProjection",
    "configuration_text",
    "extraction_projection",
    "story_state_text",
    "world_state_text",
]
