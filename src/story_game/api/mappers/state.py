"""Translate complete API documents without leaking transport types inward."""

from __future__ import annotations

from story_game.api.schemas.common import (
    ActorProfileModel,
    ConditionModel,
    EntityLinkModel,
    FactModel,
    GameConfigurationModel,
    GameRunMemberModel,
    GameRunModel,
    GoalModel,
    KnowledgeEntryModel,
    StorySummaryModel,
    StoryTurnModel,
    VisibilityModel,
    WorldEntityModel,
    WorldRuleModel,
)
from story_game.api.schemas.state import (
    GameDocument,
    GameStateModel,
    StoryStateModel,
    WorldStateModel,
)
from story_game.application.game_models import LoadedGame
from story_game.domain import (
    ActorProfile,
    Condition,
    EntityLink,
    Fact,
    GameConfiguration,
    GameRun,
    GameRunMember,
    GameState,
    Goal,
    KnowledgeEntry,
    PromptProfile,
    StableId,
    StateRevision,
    StorySequence,
    StoryState,
    StorySummary,
    StoryTurn,
    Visibility,
    WorldEntity,
    WorldRule,
    WorldState,
)


def game_from_api(document: GameDocument) -> LoadedGame:
    run_model = document.game_run
    state_model = document.game_state
    run = GameRun(
        StableId(run_model.id),
        run_model.name,
        run_model.status,
        StateRevision(run_model.current_revision),
        tuple(
            GameRunMember(
                member.issuer,
                member.subject,
                member.game_role,
                None
                if member.player_entity_id is None
                else StableId(member.player_entity_id),
            )
            for member in run_model.members
        ),
        run_model.created_at,
        run_model.updated_at,
    )
    state = GameState(
        StableId(state_model.run_id),
        StateRevision(state_model.revision),
        _configuration_from_api(state_model.configuration),
        _world_from_api(state_model.world),
        _story_from_api(state_model.story),
    )
    return LoadedGame(run, state)


def game_to_api(game: LoadedGame) -> GameDocument:
    run = game.run
    state = game.state
    return GameDocument(
        game_run=GameRunModel(
            id=run.id.value,
            name=run.name,
            status=run.status,
            current_revision=run.current_revision.value,
            members=[
                GameRunMemberModel(
                    issuer=member.issuer,
                    subject=member.subject,
                    game_role=member.game_role,
                    player_entity_id=(
                        None
                        if member.player_entity_id is None
                        else member.player_entity_id.value
                    ),
                )
                for member in run.members
            ],
            created_at=run.created_at,
            updated_at=run.updated_at,
        ),
        game_state=GameStateModel(
            run_id=state.run_id.value,
            revision=state.revision.value,
            configuration=_configuration_to_api(state.configuration),
            world=_world_to_api(state.world),
            story=_story_to_api(state.story),
        ),
    )


def _configuration_from_api(model: GameConfigurationModel) -> GameConfiguration:
    return GameConfiguration(
        language=model.language,
        prompt_profile=PromptProfile(
            genre=model.prompt_profile.genre,
            tone=model.prompt_profile.tone,
            prose_style=model.prompt_profile.prose_style,
            perspective=model.prompt_profile.perspective,
            pacing=model.prompt_profile.pacing,
            control_mode=model.prompt_profile.control_mode,
            player_agency=model.prompt_profile.player_agency,
            consequence=model.prompt_profile.consequence,
            challenge=model.prompt_profile.challenge,
            content_profile=model.prompt_profile.content_profile,
        ),
        narrative_boundaries=tuple(model.narrative_boundaries),
        prompt_package_id=model.prompt_package_id,
        prompt_package_version=model.prompt_package_version,
    )


def _configuration_to_api(value: GameConfiguration) -> GameConfigurationModel:
    return GameConfigurationModel(
        language=value.language,
        prompt_profile={
            "genre": value.prompt_profile.genre,
            "tone": value.prompt_profile.tone,
            "prose_style": value.prompt_profile.prose_style,
            "perspective": value.prompt_profile.perspective,
            "pacing": value.prompt_profile.pacing,
            "control_mode": value.prompt_profile.control_mode,
            "player_agency": value.prompt_profile.player_agency,
            "consequence": value.prompt_profile.consequence,
            "challenge": value.prompt_profile.challenge,
            "content_profile": value.prompt_profile.content_profile,
        },
        narrative_boundaries=list(value.narrative_boundaries),
        prompt_package_id=value.prompt_package_id,
        prompt_package_version=value.prompt_package_version,
    )


def _visibility_from_api(model: VisibilityModel) -> Visibility:
    return Visibility(
        model.scope,
        None if model.actor_id is None else StableId(model.actor_id),
    )


def _visibility_to_api(value: Visibility) -> VisibilityModel:
    return VisibilityModel(
        scope=value.scope,
        actor_id=None if value.actor_id is None else value.actor_id.value,
    )


def _world_from_api(model: WorldStateModel) -> WorldState:
    return WorldState(
        entities=tuple(
            WorldEntity(
                StableId(item.id),
                item.kind,
                item.label,
                item.description,
                None if item.actor is None else ActorProfile(item.actor.role),
                tuple(Condition(value.name, value.description) for value in item.conditions),
                tuple(item.aliases),
            )
            for item in model.entities
        ),
        links=tuple(
            EntityLink(
                StableId(item.id),
                StableId(item.source_id),
                StableId(item.target_id),
                item.kind,
                _visibility_from_api(item.visibility),
                item.quantity,
                item.description,
            )
            for item in model.links
        ),
        facts=tuple(
            Fact(
                id=StableId(item.id),
                statement=item.statement,
                visibility=_visibility_from_api(item.visibility),
                subject_id=(
                    None if item.subject_id is None else StableId(item.subject_id)
                ),
            )
            for item in model.facts
        ),
        knowledge=tuple(
            KnowledgeEntry(
                StableId(item.actor_id),
                StableId(item.fact_id),
                StorySequence(item.learned_at),
                None
                if item.forgotten_at is None
                else StorySequence(item.forgotten_at),
            )
            for item in model.knowledge
        ),
        rules=tuple(
            WorldRule(
                id=StableId(item.id),
                statement=item.statement,
                visibility=_visibility_from_api(item.visibility),
            )
            for item in model.rules
        ),
        goals=tuple(
            Goal(
                StableId(item.id),
                item.kind,
                item.title,
                item.description,
                item.status,
                tuple(StableId(reference) for reference in item.related_entity_ids),
            )
            for item in model.goals
        ),
        scene_location_ids=tuple(
            StableId(reference) for reference in model.scene_location_ids
        ),
    )


def _world_to_api(world: WorldState) -> WorldStateModel:
    return WorldStateModel(
        entities=[
            WorldEntityModel(
                id=item.id.value,
                kind=item.kind,
                label=item.label,
                description=item.description,
                actor=(
                    None if item.actor is None else ActorProfileModel(role=item.actor.role)
                ),
                conditions=[
                    ConditionModel(name=value.name, description=value.description)
                    for value in item.conditions
                ],
                aliases=list(item.aliases),
            )
            for item in world.entities
        ],
        links=[
            EntityLinkModel(
                id=item.id.value,
                source_id=item.source_id.value,
                target_id=item.target_id.value,
                kind=item.kind,
                visibility=_visibility_to_api(item.visibility),
                quantity=item.quantity,
                description=item.description,
            )
            for item in world.links
        ],
        facts=[
            FactModel(
                id=item.id.value,
                statement=item.statement,
                visibility=_visibility_to_api(item.visibility),
                subject_id=None if item.subject_id is None else item.subject_id.value,
            )
            for item in world.facts
        ],
        knowledge=[
            KnowledgeEntryModel(
                actor_id=item.actor_id.value,
                fact_id=item.fact_id.value,
                learned_at=item.learned_at.value,
                forgotten_at=(
                    None if item.forgotten_at is None else item.forgotten_at.value
                ),
            )
            for item in world.knowledge
        ],
        rules=[
            WorldRuleModel(
                id=item.id.value,
                statement=item.statement,
                visibility=_visibility_to_api(item.visibility),
            )
            for item in world.rules
        ],
        goals=[
            GoalModel(
                id=item.id.value,
                kind=item.kind,
                title=item.title,
                description=item.description,
                status=item.status,
                related_entity_ids=[reference.value for reference in item.related_entity_ids],
            )
            for item in world.goals
        ],
        scene_location_ids=[
            reference.value for reference in world.scene_location_ids
        ],
    )


def _story_from_api(model: StoryStateModel) -> StoryState:
    return StoryState(
        turns=tuple(
            StoryTurn(
                StableId(item.id),
                StorySequence(item.sequence),
                item.player_input,
                item.narration,
                StateRevision(item.based_on_revision),
                StateRevision(item.resulting_revision),
                item.completed_at,
            )
            for item in model.turns
        ),
        summary=(
            None
            if model.summary is None
            else StorySummary(
                StorySequence(model.summary.through_sequence),
                model.summary.text,
                StateRevision(model.summary.based_on_revision),
            )
        ),
        current_turn_sequence=model.current_turn_sequence,
    )


def _story_to_api(story: StoryState) -> StoryStateModel:
    return StoryStateModel(
        turns=[
            StoryTurnModel(
                id=item.id.value,
                sequence=item.sequence.value,
                player_input=item.player_input,
                narration=item.narration,
                based_on_revision=item.based_on_revision.value,
                resulting_revision=item.resulting_revision.value,
                completed_at=item.completed_at,
            )
            for item in story.turns
        ],
        summary=(
            None
            if story.summary is None
            else StorySummaryModel(
                through_sequence=story.summary.through_sequence.value,
                text=story.summary.text,
                based_on_revision=story.summary.based_on_revision.value,
            )
        ),
        current_turn_sequence=story.current_turn_sequence,
    )
