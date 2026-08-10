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
