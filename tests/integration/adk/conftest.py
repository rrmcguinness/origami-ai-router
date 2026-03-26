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
import pytest
from typing import Dict
from fastapi.testclient import TestClient

# Local imports
from origami_router.main import app
from origami_api.config import Config
from origami_common.otel import init_otel, flush_otel

# ADK imports
from google.adk.agents.llm_agent import Agent

@pytest.fixture(scope="module")
def rules_data():
    """Loads and returns the rules.toml configuration."""
    rules_path = os.path.join(os.path.dirname(__file__), "../../../rules.toml")
    if not os.path.exists(rules_path):
        rules_path = "rules.toml"
        
    try:
        with open(rules_path, "r") as f:
            return toml.load(f)
    except Exception as e:
        print(f"Warning: Failed to load rules.toml: {e}")
        return {}

def get_routing_decision(prompt: str) -> str:
    """Consults the EdgeRouter API to determine the appropriate specialist for a given prompt."""
    client = TestClient(app)
    response = client.post("/route", json={"model": "gemini", "prompt": prompt})
    if response.status_code != 200:
        return "fallback"
    return response.json().get("route", "fallback")

@pytest.fixture(scope="module")
def adk_config(rules_data):
    """Initializes the configuration and OTel."""
    os.environ["RUNTIME_ENV"] = "integration"
    
    # Pre-seed the FastAPI app's global config so it doesn't initialize a second time
    import origami_router.state as edgestate
    if edgestate.config is None:
        edgestate.config = Config()
    config = edgestate.config
    
    init_otel(config)
    
    # Extract API key and project
    if config.application.google_project_id:
        os.environ["GOOGLE_PROJECT"] = config.application.google_project_id

    router_model = config.ai_models.get_model("router")
    
    if router_model and router_model.api_key and router_model.api_key != "[ENCRYPTION_KEY]":
        os.environ["GOOGLE_API_KEY"] = router_model.api_key
    else:
        api_key_env = os.environ.get("GEMINI_API_KEY", getattr(config.application, "api_key", ""))
        os.environ["GOOGLE_API_KEY"] = api_key_env

    if not os.environ["GOOGLE_API_KEY"]:
        raise ValueError("GOOGLE_API_KEY not found in environment")
        
    model_name = router_model.model_name

    if not model_name:
        raise ValueError("Model name not found in configuration")
    
    print("\n[WARMUP] Warming up EdgeRouter and ADK to avoid cold-start latency skew in metrics...")
    # Warmup EdgeRouter (FastAPI)
    get_routing_decision("hi")
    
    # Warmup ADK
    import anyio
    from google.adk.runners import InMemoryRunner
    from google.genai import types
    
    async def _warmup_adk():
        agent = Agent(name="warmup", instruction="say hi", model=model_name)
        runner = InMemoryRunner(agent)
        runner.auto_create_session = True
        try:
            async for _ in runner.run_async(
                user_id="warmup", 
                session_id="warmup", 
                new_message=types.Content(role="user", parts=[types.Part(text="hi")])
            ):
                pass
        except Exception as e:
            print(f"[WARMUP WARNING] ADK warmup failed: {e}")
            
    anyio.run(_warmup_adk)
    print("[WARMUP] Complete.")
    
    instructions = {}
    for agent_def in rules_data.get("agents", []):
        if "name" in agent_def and "instructions" in agent_def:
            instructions[agent_def["name"]] = agent_def["instructions"].strip()

    yield {
        "model_name": model_name,
        "agent_instructions": instructions,
        "get_routing_decision": get_routing_decision
    }
    flush_otel()

@pytest.fixture(scope="module")
def root_agent(adk_config, rules_data):
    """Initializes the ADK system and returns the Root Coordinator Agent."""
    model_name = adk_config["model_name"]
    instructions_dict = adk_config["agent_instructions"]
    
    specialists = []
    for agent_def in rules_data.get("agents", []):
        name = agent_def["name"]
        description = agent_def["description"]
        instruction = instructions_dict.get(name, f"You are the {name} specialist. Your role: {description}")
        
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
        instruction="""You are the ultimate shopping concierge.
        1. ALWAYS use 'get_routing_decision' first to identify the right specialized agent. (The router backend natively provides deep reasoning.)
        2. Transfer the user's request to that agent using the 'transfer_to_agent' tool.
        3. Do not try to solve complex specialist tasks yourself; you are the coordinator.""",
        model=model_name,
        tools=[get_routing_decision],
        sub_agents=specialists
    )
    
    return root
