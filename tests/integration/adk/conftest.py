import os
import toml
import pytest
from typing import Dict
from fastapi.testclient import TestClient

# Local imports
from edgerouter.main import app
from edgerouter_api.config import Config
from common.otel import init_otel, flush_otel

# ADK imports
from google.adk.agents.llm_agent import Agent

# Specialist Instructions (Cleaned of Walmart-specific references)
AGENT_INSTRUCTIONS: Dict[str, str] = {
    "us_customer_care": "You handle customer care requests related to order status, order status updates, cancellations, returns, and refunds. You answer questions about policies, services, and store locations. You are the mandatory routing destination for any request to talk to a live person, human, or agent.",
    "customer_faq_agent": "Answers general questions based exclusively on the help center and self-service web pages. Covers memberships, privacy policies, gift cards, warranties, and price matching.",
    "general_knowledge": "Provides general information, advice, or trivia using world knowledge. Useful when there is a search that should not be disrupted. Does not handle order-specific queries.",
    "fallback": "Handles out-of-scope requests, inappropriate topics, cart operations (add/remove/checkout), and chatbot persona inquiries.",
    "decision_assistant": "Answers detailed questions specifically about the product on the current item page (specs, warranty, reviews).",
    "carousel_qna": "Provides information and comparisons about products actively displayed in the current carousel.",
    "shopping_tool": "The primary engine for finding products, refining searches, and displaying new carousels.",
    "events_shopping_planner": "Assists in planning events, gatherings, or specific personal routines, curating relevant products.",
    "essentials": "Your exclusive task is to present the 'essentials' carousel when the user explicitly asks for their usuals, regular shopping, go-to items, or weekly prep. Do not handle requests to modify specific items inside the essentials list, cart modifications, or general browsing.",
    "auto_care_center": "You exclusively handle generic tire shopping intent, numeric tire sizes (e.g., 235/45R18), tire-vehicle fitment, and tire seasonality (winter, all-season). Do not handle queries regarding auto/tire services (installation, oil changes), DIY advice, warranties, or tire attributes beyond seasonality (e.g., touring, performance, terrain).",
    "recipe_agent": "You handle explicit requests to make, cook, bake, or prepare food. You refine active recipe searches based on budget, ingredients, substitutions, dietary restrictions, and serving sizes. Do not handle requests for ready-to-eat/deli foods, generic kitchen equipment, or instances where the user states they do not want to cook."
}

def get_routing_decision(prompt: str) -> str:
    """Consults the EdgeRouter API to determine the appropriate specialist for a given prompt."""
    client = TestClient(app)
    response = client.post("/route", json={"model": "gemini", "prompt": prompt})
    if response.status_code != 200:
        return "fallback"
    return response.json().get("route", "fallback")

@pytest.fixture(scope="module")
def adk_config():
    """Initializes the configuration and OTel."""
    os.environ["RUNTIME_ENV"] = "integration"
    
    # Pre-seed the FastAPI app's global config so it doesn't initialize a second time
    import edgerouter.main as edgemain
    if edgemain.config is None:
        edgemain.config = Config()
    config = edgemain.config
    
    init_otel(config)
    
    # Extract API key and project
    if config.application.google_project_id:
        os.environ["GOOGLE_PROJECT"] = config.application.google_project_id

    router_model = config.ai_models.get_model("router")
    
    if router_model and router_model.api_key and router_model.api_key != "[ENCRYPTION_KEY]":
        os.environ["GOOGLE_API_KEY"] = router_model.api_key
    else:
        from tests.integration.data import get_test_env_setting
        api_key_env = get_test_env_setting("api_key")
        os.environ["GOOGLE_API_KEY"] = api_key_env or "dummy_key_to_avoid_startup_crash"
        
    model_name = router_model.model_name or "gemini-3.1-flash-lite-preview" if router_model else "gemini-3.1-flash-lite-preview"
    
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
    
    yield {
        "model_name": model_name,
        "agent_instructions": AGENT_INSTRUCTIONS,
        "get_routing_decision": get_routing_decision
    }
    flush_otel()

@pytest.fixture(scope="module")
def root_agent(adk_config):
    """Initializes the ADK system and returns the Root Coordinator Agent."""
    model_name = adk_config["model_name"]
    
    # Load sub-agents from rules.toml
    rules_path = os.path.join(os.path.dirname(__file__), "../../../rules.toml")
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
        instruction="""You are the ultimate shopping concierge.
        1. ALWAYS use 'get_routing_decision' first to identify the right specialized agent.
        2. Transfer the user's request to that agent using the 'transfer_to_agent' tool.
        3. Do not try to solve complex specialist tasks yourself; you are the coordinator.""",
        model=model_name,
        tools=[get_routing_decision],
        sub_agents=specialists
    )
    
    return root
