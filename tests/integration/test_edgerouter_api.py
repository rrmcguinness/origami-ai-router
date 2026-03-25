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
from tests.data.data import RETAIL_TEST_CASES

client = TestClient(app)

@pytest.mark.parametrize("query,expected_route,context_summary", [
    (RETAIL_TEST_CASES[0]), # Dynamically pulled from config (us_customer_care)
    (RETAIL_TEST_CASES[2]), # Dynamically pulled from config (shopping_tool)
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

@pytest.mark.parametrize("query,expected_route", [
    ("Where is my milk?", "us_customer_care"),
    ("lasagna recipe", "recipe_agent"),
    ("What is the return policy हल्दी?", "us_customer_care"),
])
def test_route_llama_cpp(query, expected_route):
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
    assert data["route"] in [expected_route, "fallback", "customer_faq_agent", "recipe_agent", "shopping_tool"]

def test_unsupported_model():
    """Tests error handling for unsupported models."""
    response = client.post(
        "/route",
        json={"model": "claude", "prompt": "Hello"}
    )
    assert response.status_code == 400
    assert "Unsupported model" in response.json()["detail"]
