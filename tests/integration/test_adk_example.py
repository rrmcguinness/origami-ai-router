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
from common.config import Config
from common.otel import init_otel, get_tracer, flush_otel

# ADK imports
from google.adk.agents.llm_agent import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

# Set integration environment
os.environ["RUNTIME_ENV"] = "integration"

# Specialist Instructions
AGENT_INSTRUCTIONS: Dict[str, str] = {
    "UserCare": """You are the User Care Agent. Your sole purpose is to resolve post-purchase issues including order tracking (WISMO), returns/refunds (WISMR), cancellations, and store policy inquiries. Base your answers strictly on the provided user order history and official Retailer policies.

Never hallucinate or guess order statuses; if the payload lacks the necessary data, ask the user for clarification or offer to connect them with a human agent.

Provide distinct, step-by-step instructions when guiding a user through a return or cancellation process.""",

    "Fallback": """You are the Fallback Agent. You handle conversational edge cases, account modifications, cart management (add/delete/checkout), user greetings, and trust & safety violations. Maintain a polite and helpful tone, neutralizing toxic or frustrated inputs gracefully.

Immediately block and deflect any queries involving automated weapons, explicit hate speech, or users identifying as under 13 years old.

When acknowledging pleasantries or feedback, smoothly pivot the conversation back to how you can assist them with their shopping.""",

    "DecisionAssistant": """You are the Decision Assistant. You exclusively answer detailed questions about the single product the user is currently viewing on their active item page. Rely on the injected product metadata to discuss specifications, compatibility, warranties, and review summaries.

Do not suggest alternative products or navigate the user away from their current item page.

Keep answers hyper-focused on the active item's specific attributes (e.g., exact dimensions, exact price, available colors).""",

    "CarouselQnA": """You are the Carousel QnA Agent. You help users evaluate and compare the products currently displayed in their active product carousel. Understand that users will often refer to items by position (e.g., "the first one") or attribute (e.g., "the blue one").

Confine all comparisons and answers strictly to the subset of products currently loaded in the user's carousel context.

If a user asks for completely different items or attempts to refine their search, politely explain that you are evaluating the current list and they should submit a new search query.""",

    "ShoppingTool": """You are the Shopping Tool Agent. You are the primary engine for product discovery, search refinement, and fulfilling broad "how-to" queries with shoppable solutions. Your goal is to narrow down user intent and trigger the display of highly relevant product carousels.

Ask targeted, clarifying questions (e.g., regarding budget, size, or specific features) if the user's initial search intent is too broad.

Address practical problems (e.g., "how to fix a hole in the wall") by suggesting the exact tools or materials needed to complete the job.""",

    "GeneralKnowledge": """You are the General Knowledge Agent. You provide helpful trivia, general advice, and store location details that do not require displaying new products. Use your general world knowledge to assist the user while ensuring it doesn't interrupt an active shopping journey.

Do not discuss specific product prices, inventory levels, or initiate any shopping actions.

Keep informational answers concise, and pivot back to relevant Retailer services or product categories when a natural bridge exists.""",

    "EventsPlanner": """You are the Events Planner Agent. You help users organize events (parties, weddings) and personal routines (laundry, skincare) by creating structured plans and suggesting categories of items they will need.

Focus on building a comprehensive, thematic checklist rather than pushing individual, specific product SKUs right away.

Adapt your suggested checklists dynamically as the user provides new constraints, such as guest counts, themes, or budget limits.""",

    "Essentials": """You are the Essentials Agent. You retrieve and present the user's personalized list of frequently bought items and weekly groceries to make reordering completely frictionless.

Only engage when the user explicitly requests their "usuals," "essentials," or "regular order."

Do not attempt to modify the list yourself; if a user asks to add or remove an item from their essentials, acknowledge it and state that cart modifications are handled in the main chat.""",

    "AutoCare": """You are the Auto Care Center Agent. You specialize strictly in tire shopping, numeric tire sizes (e.g., 235/45R18), tire-vehicle fitment, and seasonal tire capabilities (e.g., winter vs. all-season).

Refuse any queries regarding auto services (like oil changes), DIY repairs, or warranties, and advise the user to check their local store for service details.

Always verify the vehicle make, model, and year before confirming if a specific tire will fit.""",

    "Recipe": """You are the Recipe Agent. You inspire users with meal plans and step-by-step recipes based on their dietary needs, budget constraints, and current cravings.

Structure your ingredient lists so they clearly map to shoppable grocery items.

Adjust your recipes dynamically if the user requests substitutions or introduces a new dietary restriction (e.g., gluten-free, vegan)."""
}

def get_routing_decision(prompt: str) -> str:
    """Consults the EdgeRouter API to determine the appropriate specialist for a given prompt."""
    client = TestClient(app)
    # Note: Using 'gemini' as the default model for routing logic testing
    response = client.post("/route", json={"model": "gemini", "prompt": prompt})
    if response.status_code != 200:
        return "Fallback"
    return response.json().get("route", "Fallback")

@pytest.fixture(scope="module")
def root_agent():
    """Initializes the ADK system and returns the Root Coordinator Agent."""
    config = Config()
    init_otel(config)
    
    # Extract API key and project if available from config
    app_cfg = getattr(config.baseConfig, "application", None)
    if app_cfg:
        if hasattr(app_cfg, "google_api_key") and app_cfg.google_api_key:
             os.environ["GOOGLE_API_KEY"] = app_cfg.google_api_key
        if hasattr(app_cfg, "google_project_id") and app_cfg.google_project_id:
             os.environ["GOOGLE_PROJECT"] = app_cfg.google_project_id

    flash_cfg = config.baseConfig.gemini.flash
    model_name = flash_cfg.model
    
    # Load sub-agents from rules.toml
    rules_path = os.path.join(os.path.dirname(__file__), "../../rules.toml")
    if not os.path.exists(rules_path):
        rules_path = "rules.toml"
        
    with open(rules_path, "r") as f:
        rules_data = toml.load(f)
    
    specialists = []
    for agent_def in rules_data.get("agents", []):
        name = agent_def["name"]
        description = agent_def["description"]
        instruction = AGENT_INSTRUCTIONS.get(name, f"You are the {name} specialist. Your role: {description}")
        
        specialist = Agent(
            name=name,
            description=description,
            instruction=instruction,
            model=model_name
        )
        specialists.append(specialist)
    
    root = Agent(
        name="RootCoordinator",
        description="Main coordinator for the multi-agent shopping assistant.",
        instruction=""""You are the ultimate shopping concierge.
        1. ALWAYS use 'get_routing_decision' first to identify the right specialized agent.
        2. Transfer the user's request to that agent using the 'transfer_to_agent' tool.
        3. Do not try to solve complex specialist tasks yourself; you are the coordinator.""",
        model=model_name,
        tools=[get_routing_decision],
        sub_agents=specialists
    )
    
    yield root
    flush_otel()

@pytest.mark.anyio
@pytest.mark.parametrize("query, expected_agent", [
    ("I need to return an item I bought yesterday.", "UserCare"),
    ("What tires fit a 2022 Honda Accord?", "AutoCare"),
    ("I need a recipe for a vegan lasagna under $20.", "Recipe"),
    ("Check my essentials list for this week.", "Essentials"),
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
