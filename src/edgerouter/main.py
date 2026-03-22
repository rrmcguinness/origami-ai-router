import argparse
import json
import uvicorn
import toml
from typing import Optional, Dict, Any
import anyio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .routes import auth
from common.config import Config
from common.otel import init_otel, get_tracer
from opentelemetry.propagate import extract
from stateless_router.interface import StatelessRouter
from stateless_router.models import RoutingRules, AgentDefinition
from stateless_router.builder import RouterBuilder
from gemini_router.main import GeminiRouter
from vllm_router.main import VllmRouter
from llama_cpp_router.main import LlamaCppRouter, LlamaCppWorkerPool

# Pydantic models for the API request/response
class RouteRequest(BaseModel):
    model: str
    prompt: str

class RouteResponse(BaseModel):
    route: str

app = FastAPI(title="EdgeRouter Service", description="Aggregator for Gemini and Gemma routers.", version="1.0.0")

# Global variables for routers and config
active_routers: Dict[str, StatelessRouter] = {}
config = None
tracer = None

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

async def setup_routers(server_cfg, rules: RoutingRules):
    """Parses [[server.routers]] configuration and provisions the active_routers dictionary."""
    global active_routers
    if not server_cfg or not hasattr(server_cfg, "routers"):
        print("WARNING: No [[server.routers]] defined in configuration. Routing will fail.")
        return

    router_configs = server_cfg.routers

    for r_cfg in router_configs:
        name = getattr(r_cfg, "name", None) if hasattr(r_cfg, "name") else r_cfg.get("name")
        provider = getattr(r_cfg, "provider", None) if hasattr(r_cfg, "provider") else r_cfg.get("provider")
        
        if not name or not provider:
            print(f"Skipping invalid router config: {r_cfg}")
            continue
            
        print(f"Initializing router '{name}' via provider '{provider}'...")
        
        if provider == "gemini":
            active_routers[name] = (RouterBuilder()
                                    .with_provider(GeminiRouter)
                                    .with_rules(rules)
                                    .build())
                                    
        elif provider == "auto_local":
            model_path = getattr(r_cfg, "model_path", None) if hasattr(r_cfg, "model_path") else r_cfg.get("model_path")
            n_threads = getattr(r_cfg, "n_threads", 4) if hasattr(r_cfg, "n_threads") else r_cfg.get("n_threads", 4)
            
            try:
                import torch
                if torch.cuda.is_available():
                    print(f"  CUDA detected for '{name}', initializing VllmRouter.")
                    active_routers[name] = VllmRouter(rules, model_path=model_path)
                else:
                    raise RuntimeError("CUDA not available")
            except Exception as e:
                print(f"  Falling back to LlamaCppWorkerPool for '{name}' due to: {e}")
                pool = LlamaCppWorkerPool(rules, model_path=model_path, num_workers=n_threads)
                await pool.initialize()
                active_routers[name] = pool
        else:
            print(f"Unknown provider '{provider}' for router '{name}'")

@app.on_event("startup")
async def startup_event():
    """Initializes routers and telemetry on startup."""
    global config, tracer, active_routers
    
    parser = argparse.ArgumentParser(description="EdgeRouter FastAPI Service")
    parser.add_argument("--rules", type=str, default="rules.toml", help="Path to the routing rules TOML file")
    args, unknown = parser.parse_known_args()
    
    config = Config()
    server_cfg = getattr(config.baseConfig, "server", None)
    
    init_otel(config)
    tracer = get_tracer("edgerouter_service")
    rules = load_rules(args.rules)
    
    await setup_routers(server_cfg, rules)
    print(f"EdgeRouter service started with rules from: {args.rules}. Active routers: {list(active_routers.keys())}")

app.include_router(auth.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/readiness")
async def readiness_check():
    global active_routers
    return {"status": "ready", "router_initialized": len(active_routers) > 0}

@app.post("/route", response_model=RouteResponse)
async def route_query(request: RouteRequest, req: Request):
    """
    Main routing endpoint.
    Participates in OTel span if provided in headers, otherwise starts a new one.
    """
    global tracer, config, active_routers
    if tracer is None:
        tracer = get_tracer("edgerouter_service")
    
    # In test environments, startup_event might not have fired
    if not active_routers:
        if config is None:
            config = Config()
        
        rules_path = "rules.toml"
        rules = load_rules(rules_path)
        server_cfg = getattr(config.baseConfig, "server", None)
        await setup_routers(server_cfg, rules)

    ctx = extract(req.headers)

    with tracer.start_as_current_span(
        "edgerouter.api_route",
        attributes={"router.model_requested": request.model},
        context=ctx
    ) as span:
        
        model_name = request.model.lower()
        target_router = active_routers.get(model_name)
        
        if not target_router:
            span.set_attribute("error", True)
            span.set_attribute("error.message", f"Router not configured for model: {request.model}")
            raise HTTPException(status_code=404, detail=f"Router not configured for model: {request.model}")

        # Execute routing dynamically based on available interface
        if hasattr(target_router, "route_async") and callable(getattr(target_router, "route_async")):
            outcome = await target_router.route_async(request.prompt)
        elif hasattr(target_router, "route") and callable(getattr(target_router, "route")):
            outcome = await anyio.to_thread.run_sync(target_router.route, request.prompt)
        else:
            span.set_attribute("error", True)
            span.set_attribute("error.message", f"Invalid router interface for {request.model}")
            raise HTTPException(status_code=500, detail=f"Invalid router interface for {request.model}")
            
        span.set_attribute("router.outcome", outcome)
        return RouteResponse(route=outcome)

if __name__ == "__main__":
    # Load config for uvicorn settings
    cfg = Config()
    server_cfg = getattr(cfg.baseConfig, "server", None)
    host = getattr(server_cfg, "host", "0.0.0.0")
    port = getattr(server_cfg, "port", 8000)
    
    uvicorn.run(app, host=host, port=port)
