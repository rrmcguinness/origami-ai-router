import pytest
from fastapi.testclient import TestClient
from edgerouter.main import app
from tests.integration.data import RETAIL_TEST_CASES

client = TestClient(app)

@pytest.mark.parametrize("query,expected_route", [
    (RETAIL_TEST_CASES[0]), # Dynamically pulled from config (CustomerCare)
    (RETAIL_TEST_CASES[2]), # Dynamically pulled from config (ShoppingTool)
])
def test_route_gemini(query, expected_route):
    """Tests routing with Gemini using configuration-driven query/response pairs."""
    response = client.post(
        "/route",
        json={"model": "gemini", "prompt": query}
    )
    assert response.status_code == 200
    data = response.json()
    assert "route" in data
    # We allow for some model variance, but the outcome should be the expected route or Fallback
    assert data["route"] in [expected_route, "Fallback"]

@pytest.mark.parametrize("query,expected_route", [
    (RETAIL_TEST_CASES[1]), # Dynamically pulled from config (CustomerCare)
    (RETAIL_TEST_CASES[3]), # Dynamically pulled from config (DecisionAssistant)
])
def test_route_gemma(query, expected_route):
    """Tests routing with Gemma using configuration-driven query/response pairs."""
    response = client.post(
        "/route",
        json={"model": "gemma", "prompt": query}
    )
    assert response.status_code == 200
    data = response.json()
    assert "route" in data
    assert data["route"] in [expected_route, "Fallback"]

def test_unsupported_model():
    """Tests error handling for unsupported models."""
    response = client.post(
        "/route",
        json={"model": "claude", "prompt": "Hello"}
    )
    assert response.status_code == 400
    assert "Unsupported model" in response.json()["detail"]
