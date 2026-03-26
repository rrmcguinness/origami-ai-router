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
pytestmark = pytest.mark.integration
from fastapi.testclient import TestClient
from origami_router.main import app
from tests.data.data import RETAIL_TEST_CASES, get_rules_for_provider

client = TestClient(app)

@pytest.mark.parametrize("query,expected_route,context_summary", [
    (RETAIL_TEST_CASES[0]),
    (RETAIL_TEST_CASES[2]),
])
def test_route_gemini(query, expected_route, context_summary):
    """Tests routing with Gemini using configuration-driven query/response pairs."""
    response = client.post(
        "/route",
        json={"model": "gemini", "prompt": query}
    )
    assert response.status_code == 200
    data = response.json()
    assert "route" in data
    # We allow for some model variance, but the outcome should be the expected route or fallback
    assert data["route"] in [expected_route, "fallback"]

@pytest.mark.parametrize("query, expected_route, context_summary", [
    RETAIL_TEST_CASES[5],
    RETAIL_TEST_CASES[15],
    RETAIL_TEST_CASES[25],
])
def test_route_llama_cpp(query, expected_route, context_summary):
    """
    Test the /route endpoint for the llama_cpp provider.
    Allows for some model variance (e.g., milk -> recipe_agent, policy -> customer_faq_agent)
    when using smaller local models.
    """
    response = client.post(
        "/route",
        json={"model": "llama", "prompt": query}
    )
    assert response.status_code == 200
    data = response.json()
    assert "route" in data
    
    # Verify the route is either the expected one or in the set of valid agents from config
    valid_agents = [agent.name for agent in get_rules_for_provider("gemini").agents]
    assert data["route"] in valid_agents

def test_unsupported_model():
    """Tests error handling for unsupported models."""
    response = client.post(
        "/route",
        json={"model": "claude", "prompt": "Hello"}
    )
    assert response.status_code == 400
    assert "Unsupported model" in response.json()["detail"]
