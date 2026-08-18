from __future__ import annotations

from fastapi.testclient import TestClient

from tests.api.test_api import client, store  # noqa: F401 - reused fixtures


def test_openapi_describes_the_run_lifecycle(
    client: TestClient,
) -> None:
    schema = client.get("/openapi.json").json()

    assert schema["paths"]["/api/v1/runs"]["get"]
    assert schema["paths"]["/api/v1/runs"]["post"]
    assert schema["paths"]["/api/v1/runs/{run_id}"]["get"]
    assert schema["paths"]["/api/v1/runs/{run_id}/playthroughs"]["post"]
    assert schema["paths"]["/api/v1/runs/{run_id}/turns"]["post"]
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
        "GameRunModel": ("id",),
        "GameStateModel": ("run_id",),
        "RunSummaryModel": ("id",),
    }
    for component, fields in component_fields.items():
        properties = schema["components"]["schemas"][component]["properties"]
        for field in fields:
            assert _contains_uuid_schema(properties[field])

    goal_references = schema["components"]["schemas"]["GoalModel"]["properties"][
        "related_entity_ids"
    ]
    assert goal_references["items"]["format"] == "uuid"

    controlled_entity_ids = schema["components"]["schemas"]["GameRunMemberModel"][
        "properties"
    ]["controlled_entity_ids"]
    assert controlled_entity_ids["items"]["format"] == "uuid"

    path_parameter = schema["paths"]["/api/v1/runs/{run_id}"]["get"]["parameters"][0]
    assert path_parameter["schema"]["format"] == "uuid"


def _contains_uuid_schema(value: dict) -> bool:
    return value.get("format") == "uuid" or any(
        option.get("format") == "uuid" for option in value.get("anyOf", ())
    )
