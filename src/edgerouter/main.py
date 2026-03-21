import argparse
import json
import uvicorn
import toml
from typing import Optional
import anyio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .routes import auth
from common.config import Config
from common.otel import init_otel, get_tracer
from stateless_router.models import RoutingRules, AgentDefinition
from stateless_router.builder import RouterBuilder
from gemini_router.main import GeminiRouter
from gemma_router.main import GemmaRouter, GemmaWorkerPool

# Pydantic models for the API request/response
class RouteRequest(BaseModel):
    model: str
    prompt: str

class RouteResponse(BaseModel):
    route: str

app = FastAPI(title="EdgeRouter Service", description="Aggregator for Gemini and Gemma routers.", version="1.0.0")

# Global variables for routers and config
gemini_router = None
gemma_router = None
config = None
tracer = None
gemma_pool = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. In prod, specify domains.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_rules(rules_path: str) -> RoutingRules:
    """Loads routing rules from a TOML file."""
    with open(rules_path, "r") as f:
        data = toml.load(f)
    
    agents = [AgentDefinition(**a) for a in data.get("agents", [])]
    global_rules = data.get("rules", {}).get("global_rules", [])
    
    return RoutingRules(agents=agents, global_rules=global_rules)

@app.on_event("startup")
async def startup_event():
    """Initializes routers and telemetry on startup."""
    global gemini_router, gemma_router, config, tracer
    
    # Parse CLI arguments (this is a bit tricky with FastAPI/uvicorn, 
    # but we'll assume they were passed to the process)
    parser = argparse.ArgumentParser(description="EdgeRouter FastAPI Service")
    parser.add_argument("--rules", type=str, default="rules.toml", help="Path to the routing rules TOML file")
    args, unknown = parser.parse_known_args()
    
    # Load configuration
    config = Config()
    server_cfg = getattr(config.baseConfig, "server", None)
    
    # Initialize OTel
    init_otel(config)
    tracer = get_tracer("edgerouter_service")
    
    # Load Routing Rules
    rules = load_rules(args.rules)
    
    # Initialize Gemini Router
    gemini_router = (RouterBuilder()
                    .with_provider(GeminiRouter)
                    .with_rules(rules)
                    .build())
    
    # Initialize Gemma Pool
    model_path = getattr(server_cfg, "model_path", None)
    gemma_pool = GemmaWorkerPool(rules, model_path=model_path, num_workers=4)
    await gemma_pool.initialize()
    
    print(f"EdgeRouter service started with rules from: {args.rules}")

app.include_router(auth.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/readiness")
async def readiness_check():
    return {"status": "ready", "router_initialized": gemini_router is not None}

@app.post("/route", response_model=RouteResponse)
async def route_query(request: RouteRequest, req: Request):
    """
    Main routing endpoint.
    Participates in OTel span if provided in headers, otherwise starts a new one.
    """
    global tracer, gemini_router, gemma_pool, config
    if tracer is None:
        tracer = get_tracer("edgerouter_service")
    
    # In test environments, startup_event might not have fired
    if gemini_router is None or gemma_router is None:
        if config is None:
            config = Config()
        
        # Determine rules path - defaulting to rules.toml for tests
        rules_path = "rules.toml"
        # We can't easily get CLI args here in a test, so we use the default
        rules = load_rules(rules_path)
        
        server_cfg = getattr(config.baseConfig, "server", None)
        
        if gemini_router is None:
            gemini_router = (RouterBuilder()
                            .with_provider(GeminiRouter)
                            .with_rules(rules)
                            .build())
        
        if gemma_pool is None:
            model_path = getattr(server_cfg, "model_path", None)
            gemma_pool = GemmaWorkerPool(rules, model_path=model_path, num_workers=4)
            # This is sync-ish in a lazy context, but we need to await it
            await gemma_pool.initialize()

    with tracer.start_as_current_span(
        "edgerouter.api_route",
        attributes={"router.model_requested": request.model}
    ) as span:
        
        target_router = None
        if request.model.lower() == "gemini":
            target_router = gemini_router
        elif request.model.lower() == "gemma":
            # Gemma uses the specialized worker pool
            outcome = await gemma_pool.route_async(request.prompt)
            span.set_attribute("router.outcome", outcome)
            return RouteResponse(route=outcome)
        else:
            span.set_attribute("error", True)
            span.set_attribute("error.message", f"Unsupported model: {request.model}")
            raise HTTPException(status_code=400, detail=f"Unsupported model: {request.model}")

        if not target_router:
            span.set_attribute("error", True)
            span.set_attribute("error.message", "Router not initialized")
            raise HTTPException(status_code=500, detail="Router not initialized")

        # Execute routing for Gemini (standard sync router)
        outcome = await anyio.to_thread.run_sync(target_router.route, request.prompt)
        span.set_attribute("router.outcome", outcome)
        return RouteResponse(route=outcome)

if __name__ == "__main__":
    # Load config for uvicorn settings
    cfg = Config()
    server_cfg = getattr(cfg.baseConfig, "server", None)
    host = getattr(server_cfg, "host", "0.0.0.0")
    port = getattr(server_cfg, "port", 8000)
    
    uvicorn.run(app, host=host, port=port)
