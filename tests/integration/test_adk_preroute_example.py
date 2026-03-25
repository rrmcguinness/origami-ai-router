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
import time
import toml
import pytest
import asyncio
from typing import List, Dict
from fastapi.testclient import TestClient

# Local imports
from edgerouter.main import app
from common.config import Config
from common.otel import init_otel, get_tracer, flush_otel

# ADK imports
from google.adk.agents.llm_agent import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

# Set integration environment
os.environ["RUNTIME_ENV"] = "integration"

# Specialist Instructions (Mirroring those in test_adk_example.py but available for pre-routing)
AGENT_INSTRUCTIONS: Dict[str, str] = {
    "UserCare": """You are the User Care Agent. Your sole purpose is to resolve post-purchase issues including order tracking (WISMO), returns/refunds (WISMR), cancellations, and store policy inquiries. Base your answers strictly on the provided user order history and official Retailer policies.""",
    "AutoCare": """You are the Auto Care Center Agent. You specialize strictly in tire shopping, numeric tire sizes (e.g., 235/45R18), tire-vehicle fitment, and seasonal tire capabilities (e.g., winter vs. all-season).""",
    "Recipe": """You are the Recipe Agent. You inspire users with meal plans and step-by-step recipes based on their dietary needs, budget constraints, and current cravings.""",
    "Essentials": """You are the Essentials Agent. You retrieve and present the user's personalized list of frequently bought items and weekly groceries to make reordering completely frictionless.""",
    "Fallback": """You are the Fallback Agent. You handle conversational edge cases, account modifications, cart management, and general greetings."""
}

def get_routing_decision(prompt: str) -> str:
    """Consults the EdgeRouter API to determine the appropriate specialist for a given prompt."""
    client = TestClient(app)
    response = client.post("/route", json={"model": "gemini", "prompt": prompt})
    if response.status_code != 200:
        return "Fallback"
    return response.json().get("route", "Fallback")

@pytest.fixture(scope="module")
def test_setup():
    """Initializes the configuration and OTel."""
    config = Config()
    init_otel(config)
    
    # Extract API key and project
    app_cfg = getattr(config.baseConfig, "application", None)
    if app_cfg:
        if hasattr(app_cfg, "google_api_key") and app_cfg.google_api_key:
             os.environ["GOOGLE_API_KEY"] = app_cfg.google_api_key
        if hasattr(app_cfg, "google_project_id") and app_cfg.google_project_id:
             os.environ["GOOGLE_PROJECT"] = app_cfg.google_project_id

    flash_cfg = config.baseConfig.gemini.flash
    model_name = flash_cfg.model
    
    yield {"model_name": model_name}
    flush_otel()

@pytest.mark.anyio
@pytest.mark.parametrize("query, expected_agent", [
    ("I need to return an item I bought yesterday.", "UserCare"),
    ("What tires fit a 2022 Honda Accord?", "AutoCare"),
    ("I need a recipe for a vegan lasagna under $20.", "Recipe"),
    ("Check my essentials list for this week.", "Essentials"),
])
async def test_adk_preroute_performance(test_setup, query, expected_agent):
    """
    Measures the TTFR of the pre-routing approach:
    Call Router -> Initialize Agent with Route -> Call LLM.
    """
    model_name = test_setup["model_name"]
    tracer = get_tracer("adk-performance-test")
    
    with tracer.start_as_current_span(
        "test_adk_preroute_performance",
        attributes={"query": query, "expected_agent": expected_agent}
    ):
        overall_start = time.perf_counter()
        
        # 1. Pre-routing step
        route_start = time.perf_counter()
        route = get_routing_decision(query)
        route_duration = (time.perf_counter() - route_start) * 1000
        
        # 2. Agent Initialization with Pre-Route
        base_instruction = AGENT_INSTRUCTIONS.get(route, f"You are the {route} specialist.")
        final_instruction = f"Using the following agent: {route}\n\n{base_instruction}"
        
        agent = Agent(
            name=route,
            description=f"Specialized agent for {route}",
            instruction=final_instruction,
            model=model_name
        )
        
        runner = InMemoryRunner(agent)
        runner.auto_create_session = True
        
        new_message = types.Content(role="user", parts=[types.Part(text=query)])
        
        # 3. LLM Invocation
        llm_start = time.perf_counter()
        response_gen = runner.run_async(
            user_id="test_user", 
            session_id=f"preroute_session_{os.urandom(4).hex()}",
            new_message=new_message
        )
        
        first_token_time = None
        events = []
        async for event in response_gen:
            if first_token_time is None:
                # First event with content signifies the "First Response"
                if event.content and event.content.parts:
                    first_token_time = time.perf_counter()
            events.append(event)
            
        overall_end = time.perf_counter()
        
        # Metrics Calculation
        ttfr = (first_token_time - overall_start) * 1000 if first_token_time else 0
        pure_llm_ttfr = (first_token_time - llm_start) * 1000 if first_token_time else 0
        total_duration = (overall_end - overall_start) * 1000
        
        print(f"\n[QUERY]: {query}")
        print(f"[ROUTE]: {route} ({route_duration:.2f}ms)")
        print(f"[TTFR]: {ttfr:.2f}ms (Pure LLM: {pure_llm_ttfr:.2f}ms)")
        print(f"[TOTAL]: {total_duration:.2f}ms")
        
        # Assertions
        assert route == expected_agent, f"Pre-routing failed: expected {expected_agent}, got {route}"
        assert len(events) > 0, "Agent failed to produce any events"
        
        # Verify no tool calls were made (since we pre-routed)
        tool_calls = []
        for event in events:
            fc_calls = event.get_function_calls()
            if fc_calls:
                tool_calls.extend([fc.name for fc in fc_calls])
        
        assert len(tool_calls) == 0, f"Unexpected tool calls in pre-routed test: {tool_calls}"
