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
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from origami_api.config import Config
from origami_common.otel import init_otel, get_tracer
from origami_router import state
from .routes import auth, health, readiness, route

app = FastAPI(title="EdgeRouter Service", description="Aggregator for Gemini and Gemma routers.", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. In prod, specify domains.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initializes routers and telemetry on startup."""
    parser = argparse.ArgumentParser(description="EdgeRouter FastAPI Service")
    parser.add_argument("--rules", type=str, default="rules.toml", help="Path to the routing rules TOML file (overrides config)")
    args, unknown = parser.parse_known_args()
    
    if state.config is None:
        state.config = Config()
        
    shared_executor = state.get_executor()
    
    server_cfg = getattr(state.config, "server", None)
    
    init_otel(state.config)
    state.tracer = get_tracer("edgerouter_service")
    rules_path = args.rules if args.rules else getattr(state.config.application, "rules_file", "rules.toml")
    rules = state.load_rules(rules_path)
    
    await state.setup_routers(server_cfg, rules, shared_executor)
    print(f"EdgeRouter service started with rules from: {rules_path}. Active routers: {list(state.active_routers.keys())}")

@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shuts down the global executor and active routers."""
    for router_name, router in state.active_routers.items():
        try:
            if hasattr(router, "close"):
                import asyncio
                if asyncio.iscoroutinefunction(router.close):
                    await router.close()
                else:
                    router.close()
        except Exception as e:
            print(f"Error closing router {router_name}: {e}")
            
    if state.executor:
        print("Shutting down EdgeRouter thread pool...")
        state.executor.shutdown(wait=True)

app.include_router(auth.router)
app.include_router(health.router)
app.include_router(readiness.router)
app.include_router(route.router)

if __name__ == "__main__":
    # Load config for uvicorn settings
    cfg = Config()
    server_cfg = getattr(cfg, "server", None)
    host = getattr(server_cfg, "host", "0.0.0.0")
    port = getattr(server_cfg, "port", 8000)
    
    uvicorn.run(app, host=host, port=port)
