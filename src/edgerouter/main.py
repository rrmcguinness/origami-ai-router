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
from edgerouter_api.config import Config
from common.otel import init_otel, get_tracer
from opentelemetry.propagate import extract
from edgerouter_api.interfaces import StatelessRouter
from edgerouter_api.models import RoutingRules, AgentDefinition
from stateless_router.builder import RouterBuilder
# Imports moved inside setup_routers to allow conditional provider loading

# Pydantic models for the API request/response
class RouteRequest(BaseModel):
    model: str
    prompt: str
    context_summary: Optional[str] = None

class RouteResponse(BaseModel):
    route: str

app = FastAPI(title="EdgeRouter Service", description="Aggregator for Gemini and Gemma routers.", version="1.0.0")

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

from concurrent.futures import ThreadPoolExecutor

# Global variables for routers, config, and executor
active_routers: Dict[str, StatelessRouter] = {}
config: Optional[Config] = None
tracer = None
executor: Optional[ThreadPoolExecutor] = None

def get_executor() -> ThreadPoolExecutor:
    """Returns the global executor, initializing it if necessary."""
    global executor, config
    if executor is None:
        if config is None:
            config = Config()
        app_config = getattr(config, "application", None)
        pool_size = getattr(app_config, "threadPoolSize", 20)
        executor = ThreadPoolExecutor(max_workers=pool_size, thread_name_prefix="edge-router-pool")
    return executor

async def setup_routers(server_cfg, rules: RoutingRules, shared_executor: ThreadPoolExecutor):
    """Parses [[server.routers]] configuration and provisions the active_routers dictionary."""
    global active_routers
    
    # Conditional imports to prevent model library dependencies on all platforms
    from gemini_router.main import GeminiRouter
    
    if not server_cfg or not hasattr(server_cfg, "routers"):
        print("WARNING: No [[server.routers]] defined in configuration. Routing will fail.")
        return

    router_configs = server_cfg.routers
    if isinstance(router_configs, dict):
        router_configs = list(router_configs.values())

    for r_cfg in router_configs:
        name = getattr(r_cfg, "name", None) if hasattr(r_cfg, "name") else r_cfg.get("name")
        provider = getattr(r_cfg, "provider", None) if hasattr(r_cfg, "provider") else r_cfg.get("provider")
        
        if not name or not provider:
            print(f"Skipping invalid router config: {r_cfg}")
            continue
            
        print(f"Initializing router '{name}' via provider '{provider}'...")
        
        builder = (RouterBuilder()
                  .with_executor(shared_executor)
                  .with_rules(rules))
        
        config_path = getattr(r_cfg, "config_path", None) if hasattr(r_cfg, "config_path") else r_cfg.get("config_path")
        model_config = {}
        
        # Resolve config manually if path provided
        if config_path:
            parts = config_path.split('.')
            curr = config
            for p in parts:
                # Add backwards compatibility mapping
                if p == "gemini":
                    curr = getattr(config, "ai_models", None)
                elif p == "flash":
                    curr = getattr(curr, "get_model", lambda x: None)("router")
                else:
                    curr = getattr(curr, p, None)
            if curr:
                model_config = curr.to_dict() if hasattr(curr, "to_dict") else vars(curr)
        else:
            model_config = r_cfg.to_dict() if hasattr(r_cfg, "to_dict") else vars(r_cfg)
        
        if provider == "gemini":
            from gemini_router.main import GeminiRouter
            builder.with_provider(GeminiRouter, config=config)
            active_routers[name] = builder.build()
                                    
        elif provider == "auto_local":
            vllm_available = False
            try:
                from vllm_router.main import VllmRouter, VllmRouterConfig
                vllm_available = True
            except (ImportError, ModuleNotFoundError):
                print(f"  vLLM not available for '{name}', checking for LlamaCpp...")

            try:
                from llama_cpp_router.main import LlamaCppRouter, LlamaCppWorkerPool, LlamaCppRouterConfig
                llama_available = True
            except (ImportError, ModuleNotFoundError):
                print(f"  LlamaCpp not available for '{name}'.")
                llama_available = False

            model_path = model_config.get("model_path")
            n_threads = model_config.get("n_threads", 4)

            try:
                import torch
                if torch.cuda.is_available() and vllm_available:
                    print(f"  CUDA and vLLM detected for '{name}', initializing VllmRouter.")
                    vllm_config = VllmRouterConfig(**model_config)
                    builder.with_provider(VllmRouter, config=vllm_config)
                    active_routers[name] = builder.build()
                elif llama_available:
                    print(f"  Initializing LlamaCppWorkerPool for '{name}'.")
                    llama_config = LlamaCppRouterConfig(**model_config)
                    pool = LlamaCppWorkerPool(rules, config=llama_config, executor=shared_executor)
                    await pool.initialize()
                    active_routers[name] = pool
                else:
                    print(f"  No suitable provider found for local router '{name}'. Skipping.")
            except Exception as e:
                print(f"  Failed to initialize local router '{name}': {e}")
        else:
            print(f"Unknown provider '{provider}' for router '{name}'")

@app.on_event("startup")
async def startup_event():
    """Initializes routers and telemetry on startup."""
    global config, tracer, active_routers
    
    parser = argparse.ArgumentParser(description="EdgeRouter FastAPI Service")
    parser.add_argument("--rules", type=str, default="rules.toml", help="Path to the routing rules TOML file")
    args, unknown = parser.parse_known_args()
    
    if config is None:
        config = Config()
        
    shared_executor = get_executor()
    
    server_cfg = getattr(config, "api_server", None)
    
    init_otel(config)
    tracer = get_tracer("edgerouter_service")
    rules = load_rules(args.rules)
    
    await setup_routers(server_cfg, rules, shared_executor)
    print(f"EdgeRouter service started with rules from: {args.rules}. Active routers: {list(active_routers.keys())}")

@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shuts down the global executor."""
    global executor
    if executor:
        print("Shutting down EdgeRouter thread pool...")
        executor.shutdown(wait=True)

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
        
        shared_executor = get_executor()
        rules_path = "rules.toml"
        rules = load_rules(rules_path)
        server_cfg = getattr(config, "api_server", None)
        await setup_routers(server_cfg, rules, shared_executor)

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
            raise HTTPException(status_code=400, detail=f"Unsupported model: {request.model}")

        # Execute routing via the async interface
        try:
            outcome = await target_router.route(request.prompt, context_summary=request.context_summary)
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            raise HTTPException(status_code=500, detail=f"Routing failed: {e}")
            
        span.set_attribute("router.outcome", outcome)
        return RouteResponse(route=outcome)

if __name__ == "__main__":
    # Load config for uvicorn settings
    cfg = Config()
    server_cfg = getattr(cfg, "api_server", None)
    host = getattr(server_cfg, "host", "0.0.0.0")
    port = getattr(server_cfg, "port", 8000)
    
    uvicorn.run(app, host=host, port=port)
