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
pytestmark = pytest.mark.integration
import asyncio
from typing import List, Dict
from fastapi.testclient import TestClient

# Local imports
from origami_router.main import app
from origami_api.config import Config
from origami_common.otel import init_otel, get_tracer, flush_otel
from tests.data.data import RETAIL_TEST_CASES

# ADK imports
from google.adk.agents.llm_agent import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

# Set integration environment
os.environ["RUNTIME_ENV"] = "integration"


@pytest.mark.anyio
@pytest.mark.parametrize("query, expected_agent, context_summary", [
    RETAIL_TEST_CASES[6],
    RETAIL_TEST_CASES[16],
    RETAIL_TEST_CASES[26],
    RETAIL_TEST_CASES[36],
])
async def test_adk_preroute_performance(adk_config, query, expected_agent, context_summary):
    """
    Measures the TTFR of the pre-routing approach:
    Call Router -> Initialize Agent with Route -> Call LLM.
    """
    model_name = adk_config["model_name"]
    get_routing_decision = adk_config["get_routing_decision"]
    agent_instructions = adk_config["agent_instructions"]
    
    tracer = get_tracer("adk-performance-test")
    
    with tracer.start_as_current_span(
        "test_adk_preroute_performance",
        attributes={"query": query, "expected_agent": expected_agent}
    ):
        overall_start = time.perf_counter()
        
        # 1. Setup pre-routing callback and dynamic instruction
        metrics = {"route": None, "route_duration": 0}

        def route_interceptor(callback_context):
            with tracer.start_as_current_span("generate_route") as span:
                route_start = time.perf_counter()
                route_decision = get_routing_decision(query)
                metrics["route"] = route_decision
                metrics["route_duration"] = (time.perf_counter() - route_start) * 1000
                span.set_attribute("route", route_decision)
                callback_context.state["route"] = route_decision
            # Return None to allow agent execution to proceed
            return None

        def dynamic_instruction(context):
            r = context.state.get("route", "default_agent")
            base_instr = agent_instructions.get(r, f"You are the {r} specialist.")
            return f"Using the following agent: {r}\n\n{base_instr}"

        # 2. Agent Initialization with Callback
        agent = Agent(
            name="router_agent",
            description="Agent with dynamic routing via before_agent_callback",
            instruction=dynamic_instruction,
            model=model_name,
            before_agent_callback=route_interceptor
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

        route_decision = metrics["route"]
        route_duration = metrics["route_duration"]
        
        print(f"\n[QUERY]: {query}")
        print(f"[ROUTE]: {route_decision} ({route_duration:.2f}ms)")
        print(f"[TTFR]: {ttfr:.2f}ms (Pure LLM: {pure_llm_ttfr:.2f}ms)")
        print(f"[TOTAL]: {total_duration:.2f}ms")
        
        # Assertions
        assert route_decision == expected_agent, f"Pre-routing failed: expected {expected_agent}, got {route_decision}"
        assert len(events) > 0, "Agent failed to produce any events"
        
        # Verify no tool calls were made (since we pre-routed)
        tool_calls = []
        for event in events:
            fc_calls = event.get_function_calls()
            if fc_calls:
                tool_calls.extend([fc.name for fc in fc_calls])
        
        assert len(tool_calls) == 0, f"Unexpected tool calls in pre-routed test: {tool_calls}"
