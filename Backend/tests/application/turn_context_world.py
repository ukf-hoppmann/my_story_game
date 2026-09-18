"""One small readable world shared by the turn-context selection tests."""

from __future__ import annotations

from datetime import UTC, datetime

from story_game.domain import (
    ActorProfile,
    ActorRole,
    EntityKind,
    EntityLink,
    Fact,
    GameConfiguration,
    GameState,
    Goal,
    GoalKind,
    GoalStatus,
    KnowledgeEntry,
    PromptProfile,
    RelationKind,
    StableId,
    StateRevision,
    StorySequence,
    StoryState,
    StorySummarySegment,
    StoryTurn,
    Visibility,
    VisibilityScope,
    WorldEntity,
    WorldRule,
    WorldState,
)
from tests.ids import sid


MAREN = sid("maren")
ALMA = sid("alma")
WIRT = sid("wirt")
BRUDER = sid("bruder")
TAVERN = sid("tavern")
CAPITAL = sid("capital")
FOREST = sid("forest")
SWORD = sid("sword")
LAMP = sid("lamp")
GUILD = sid("guild")


def entities() -> tuple[WorldEntity, ...]:
    return (
        WorldEntity(
            MAREN,
            EntityKind.CHARACTER,
            "Maren",
            actor=ActorProfile(ActorRole.PLAYER),
        ),
        WorldEntity(
            ALMA,
            EntityKind.CHARACTER,
            "Alma",
            aliases=("die Kartografin",),
            actor=ActorProfile(ActorRole.NEUTRAL),
        ),
        WorldEntity(
            WIRT,
            EntityKind.CHARACTER,
            "Bertram",
            aliases=("der Wirt",),
            actor=ActorProfile(ActorRole.NEUTRAL),
        ),
        WorldEntity(
            BRUDER,
            EntityKind.CHARACTER,
            "Jonas",
            actor=ActorProfile(ActorRole.NEUTRAL),
        ),
        WorldEntity(TAVERN, EntityKind.LOCATION, "Wirtshaus"),
        WorldEntity(CAPITAL, EntityKind.LOCATION, "Hauptstadt"),
        WorldEntity(FOREST, EntityKind.LOCATION, "Schwarzwald"),
        WorldEntity(SWORD, EntityKind.ITEM, "Silberschwert"),
        WorldEntity(LAMP, EntityKind.ITEM, "Öllampe"),
        WorldEntity(GUILD, EntityKind.FACTION, "Kartografengilde"),
    )


def links() -> tuple[EntityLink, ...]:
    return (
        EntityLink(sid("l-maren-tavern"), MAREN, TAVERN, RelationKind.LOCATED_IN),
        EntityLink(sid("l-wirt-tavern"), WIRT, TAVERN, RelationKind.LOCATED_IN),
        EntityLink(sid("l-alma-forest"), ALMA, FOREST, RelationKind.LOCATED_IN),
        EntityLink(sid("l-bruder-capital"), BRUDER, CAPITAL, RelationKind.LOCATED_IN),
        EntityLink(sid("l-maren-sword"), MAREN, SWORD, RelationKind.POSSESSES),
        EntityLink(sid("l-alma-guild"), ALMA, GUILD, RelationKind.MEMBER_OF),
        # A location contains an item: the source is the container, the target
        # the contained thing. The reverse is rejected by the domain.
        EntityLink(sid("l-tavern-lamp"), TAVERN, LAMP, RelationKind.CONTAINS),
    )


def facts() -> tuple[Fact, ...]:
    return (
        Fact(sid("f-tavern-warm"), "Im Wirtshaus brennt ein Feuer.", subject_id=TAVERN),
        Fact(sid("f-wirt-secret"), "Bertram kennt den Geheimgang.", subject_id=WIRT),
        Fact(
            sid("f-wirt-plot"),
            "Bertram wird die Gruppe verraten.",
            visibility=Visibility(VisibilityScope.DIRECTOR_ONLY),
            subject_id=WIRT,
        ),
        Fact(sid("f-global"), "Der Winter kommt früh in diesem Jahr."),
        Fact(sid("f-capital-far"), "Die Hauptstadt liegt weit im Norden.", subject_id=CAPITAL),
    )


def knowledge() -> tuple[KnowledgeEntry, ...]:
    return (KnowledgeEntry(WIRT, sid("f-wirt-secret"), StorySequence(1)),)


def rules() -> tuple[WorldRule, ...]:
    return (WorldRule(sid("r-silver"), "Silber verletzt Geister."),)


def goals() -> tuple[Goal, ...]:
    return (
        Goal(
            sid("g-main"),
            GoalKind.MAIN,
            "Finde den Geheimgang",
            "Maren sucht den Geheimgang unter dem Wirtshaus.",
            GoalStatus.OPEN,
            (MAREN,),
        ),
        Goal(
            sid("g-done"),
            GoalKind.MAIN,
            "Erreiche das Wirtshaus",
            "Bereits geschafft.",
            GoalStatus.COMPLETED,
            (MAREN,),
        ),
        Goal(
            sid("g-side"),
            GoalKind.SIDE,
            "Tritt der Gilde bei",
            "Alma kann Maren empfehlen.",
            GoalStatus.OPEN,
            (ALMA, GUILD),
        ),
    )


def world(scene: tuple[StableId, ...] = (TAVERN,)) -> WorldState:
    return WorldState(
        entities=entities(),
        links=links(),
        facts=facts(),
        knowledge=knowledge(),
        rules=rules(),
        goals=goals(),
        scene_location_ids=scene,
    )


def configuration() -> GameConfiguration:
    return GameConfiguration(
        language="de",
        prompt_profile=PromptProfile(
            genre="dark_fantasy",
            tone="balanced",
            prose_style="balanced",
            perspective="second_person",
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


def turn(sequence: int, narration: str) -> StoryTurn:
    return StoryTurn(
        sid(f"turn-{sequence}"),
        StorySequence(sequence),
        f"Eingabe {sequence}",
        narration,
        StateRevision(sequence),
        StateRevision(sequence + 1),
        datetime(2026, 8, 17, tzinfo=UTC),
    )


def story(*narrations: str) -> StoryState:
    turns = tuple(
        turn(index, narration) for index, narration in enumerate(narrations, start=1)
    )
    if not turns:
        return StoryState()
    return StoryState(
        turns=turns,
        summaries=(
            StorySummarySegment(
                turns[0].sequence,
                turns[-1].sequence,
                "Maren hat das Wirtshaus erreicht.",
                turns[-1].resulting_revision,
            ),
        ),
        current_turn_sequence=len(turns),
    )


def game_state(
    scene: tuple[StableId, ...] = (TAVERN,),
    *narrations: str,
) -> GameState:
    return GameState(
        sid("run"),
        StateRevision(1),
        configuration(),
        world(scene),
        story(*narrations),
    )
