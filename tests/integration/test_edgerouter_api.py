# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
