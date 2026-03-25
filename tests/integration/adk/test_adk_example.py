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

import os
import toml
import time
import pytest
import asyncio
from typing import List, Dict
from fastapi.testclient import TestClient

# Local imports
from edgerouter.main import app
from edgerouter_api.config import Config
from common.otel import init_otel, get_tracer, flush_otel

# ADK imports
from google.adk.agents.llm_agent import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

# Set integration environment
os.environ["RUNTIME_ENV"] = "integration"


@pytest.mark.anyio
@pytest.mark.parametrize("query, expected_agent", [
    ("I need to return an item I bought yesterday.", "us_customer_care"),
    ("What tires fit a 2022 Honda Accord?", "auto_care_center"),
    ("I need a recipe for a vegan lasagna under $20.", "recipe_agent"),
    ("Check my essentials list for this week.", "essentials"),
])
async def test_adk_routing_and_execution(root_agent, query, expected_agent):
    """Verifies that the RootCoordinator correctly routes and delegates to specialists."""
    tracer = get_tracer("adk-integration-test")
    
    with tracer.start_as_current_span(
        "test_adk_routing_and_execution",
        attributes={"query": query, "expected_agent": expected_agent}
    ):
        overall_start = time.perf_counter()
        runner = InMemoryRunner(root_agent)
        runner.auto_create_session = True
        
        new_message = types.Content(role="user", parts=[types.Part(text=query)])
        
        response_gen = runner.run_async(
            user_id="test_user", 
            session_id=f"test_session_{os.urandom(4).hex()}",
            new_message=new_message
        )
        
        first_token_time = None
        events = []
        async for event in response_gen:
            if first_token_time is None:
                # First content part signifies first response
                if event.content and event.content.parts:
                    first_token_time = time.perf_counter()
            events.append(event)
            
        overall_end = time.perf_counter()
        ttfr = (first_token_time - overall_start) * 1000 if first_token_time else 0
        total_duration = (overall_end - overall_start) * 1000
        
        print(f"\n[QUERY]: {query} (DYNAMIC)")
        print(f"[TTFR]: {ttfr:.2f}ms")
        print(f"[TOTAL]: {total_duration:.2f}ms")

        # Assertions
        assert len(events) > 0, "Agent failed to produce any events"
        
        # Verify routing decision occurred
        tool_calls = []
        for event in events:
            fc_calls = event.get_function_calls()
            if fc_calls:
                tool_calls.extend([fc.name for fc in fc_calls])
        
        assert "get_routing_decision" in tool_calls, "Root agent failed to call routing tool"
        assert "transfer_to_agent" in tool_calls, "Root agent failed to transfer control"
        
        # Verify target agent
        transfer_targets = []
        for event in events:
            fc_calls = event.get_function_calls()
            if fc_calls:
                for fc in fc_calls:
                    if fc.name == "transfer_to_agent":
                        transfer_targets.append(fc.args.get("agent_name"))
        
        assert expected_agent in transfer_targets, f"Agent was routed to {transfer_targets} instead of {expected_agent}"
        
        # Verify final response contains text
        final_text = ""
        for event in events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        final_text += part.text
        
        assert len(final_text) > 20, "Agent response was too short or empty"
