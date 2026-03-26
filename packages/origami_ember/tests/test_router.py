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
import asyncio
from unittest.mock import MagicMock
from origami_api.models import RoutingRules, AgentDefinition
from origami_api.config import Config
from origami_ember.router import EmberRouter

@pytest.fixture
def mock_rules():
    return RoutingRules(
        agents=[
            AgentDefinition(
                name="Returns",
                description="Handles product returns and refund policies.",
                examples=["How do I return my order?", "Can I get a refund?"]
            ),
            AgentDefinition(
                name="Support",
                description="General technical support and account issues.",
                examples=["I can't log in.", "How do I reset my password?"]
            ),
            AgentDefinition(
                name="Office",
                description="Information about our physical locations and hours.",
                examples=["Where is your headquarters?", "What are your opening hours?"]
            )
        ]
    )

@pytest.fixture
def mock_config():
    config = MagicMock(spec=Config)
    return config

@pytest.mark.asyncio
async def test_ember_router_routing(mock_rules, mock_config):
    # We use a small model for testing if possible, but BAAI/bge-m3 is what's requested.
    # For a unit test, we might want to mock the model itself to avoid downloading a large model.
    # However, let's try a real run if the environment allows, or just mock the encoding.
    
    router = EmberRouter(mock_rules, mock_config)
    
    # Test a query related to returns
    target = await router.route("I want to send back my shoes for a refund")
    assert target == "Returns"
    
    # Test a query related to office location
    target = await router.route("What is your office address?")
    assert target == "Office"
    
    # Test a query related to support
    target = await router.route("My account is locked and I need to reset my password")
    assert target == "Support"

@pytest.mark.asyncio
async def test_ember_router_with_context(mock_rules, mock_config):
    router = EmberRouter(mock_rules, mock_config)
    
    # Query is ambiguous, but context helps
    target = await router.route("Where is it?", context_summary="The user is asking about the corporate headquarters.")
    assert target == "Office"
