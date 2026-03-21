import pytest
from fastapi.testclient import TestClient
from edgerouter.main import app

client = TestClient(app)

def test_route_gemini():
    """Tests routing with Gemini (will hit Vertex AI if credentials are set)."""
    response = client.post(
        "/route",
        json={"model": "gemini", "prompt": "Where is my order?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "route" in data
    assert data["route"] in ["CustomerCare", "ShoppingTool", "Fallback"]

def test_route_gemma():
    """Tests routing with Gemma (requires local .gguf file)."""
    response = client.post(
        "/route",
        json={"model": "gemma", "prompt": "I want to buy shoes"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "route" in data
    assert data["route"] in ["CustomerCare", "ShoppingTool", "Fallback"]

def test_unsupported_model():
    """Tests error handling for unsupported models."""
    response = client.post(
        "/route",
        json={"model": "claude", "prompt": "Hello"}
    )
    assert response.status_code == 400
    assert "Unsupported model" in response.json()["detail"]
