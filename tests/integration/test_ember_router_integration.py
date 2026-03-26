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
from origami_router.main import app

# Set integration mark
pytestmark = pytest.mark.integration

client = TestClient(app)

def test_route_ember_success():
    """
    Tests the /route endpoint using the 'ember' provider (BGE-M3).
    This depends on the 'ember' router being configured in .env.toml.
    """
    # Assuming rules.toml has some common agents like 'Customer FAQ' or 'Order Management'
    # Let's try a generic query that should match something likely to be in rules.toml
    response = client.post(
        "/route",
        json={
            "model": "ember", 
            "prompt": "I want to check my order status and track my package"
        }
    )
    if response.status_code != 200:
        print(f"Error Detail: {response.json().get('detail')}")
    assert response.status_code == 200
    data = response.json()
    assert "route" in data
    assert isinstance(data["route"], str)
    # The exact route depends on rules.toml, but it should return a string.
    print(f"Ember Router Output: {data['route']}")

def test_route_ember_with_context():
    """Tests the 'ember' router with a context summary."""
    response = client.post(
        "/route",
        json={
            "model": "ember", 
            "prompt": "Where is it?",
            "context_summary": "The user is inquiring about their recent delivery."
        }
    )
    if response.status_code != 200:
        print(f"Error Detail: {response.json().get('detail')}")
    assert response.status_code == 200
    data = response.json()
    assert "route" in data
    print(f"Ember Router (Context) Output: {data['route']}")
