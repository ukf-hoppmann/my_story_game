from __future__ import annotations

from fastapi.testclient import TestClient

from tests.api.test_api import client


def test_openapi_describes_complete_game_documents(
    client: TestClient,
) -> None:
    schema = client.get("/openapi.json").json()

    assert schema["paths"]["/api/v1/runs"]["post"]
    assert schema["paths"]["/api/v1/runs/{run_id}/state"]["get"]
    assert "/api/v1/runs/{run_id}/commits" not in schema["paths"]
    assert "GameDocument" in schema["components"]["schemas"]
    assert "EvidenceModel" not in schema["components"]["schemas"]
    component_fields = {
        "VisibilityModel": ("actor_id",),
        "WorldEntityModel": ("id",),
        "EntityLinkModel": ("id", "source_id", "target_id"),
        "FactModel": ("id", "subject_id"),
        "KnowledgeEntryModel": ("actor_id", "fact_id"),
        "WorldRuleModel": ("id",),
        "GoalModel": ("id",),
        "StoryTurnModel": ("id",),
        "GameRunMemberModel": ("player_entity_id",),
        "GameRunModel": ("id",),
        "GameStateModel": ("run_id",),
    }
    for component, fields in component_fields.items():
        properties = schema["components"]["schemas"][component]["properties"]
        for field in fields:
            assert _contains_uuid_schema(properties[field])

    goal_references = schema["components"]["schemas"]["GoalModel"]["properties"][
        "related_entity_ids"
    ]
    assert goal_references["items"]["format"] == "uuid"

    path_parameter = schema["paths"]["/api/v1/runs/{run_id}/state"]["get"][
        "parameters"
    ][0]
    assert path_parameter["schema"]["format"] == "uuid"


def _contains_uuid_schema(value: dict) -> bool:
    return value.get("format") == "uuid" or any(
        option.get("format") == "uuid" for option in value.get("anyOf", ())
    )
