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
import toml
from typing import Optional, Dict
from concurrent.futures import ThreadPoolExecutor
from origami_api.config import Config
from origami_api.interfaces import StatelessRouter
from origami_api.models import RoutingRules, AgentDefinition
from origami_stateless.builder import RouterBuilder
from origami_common.otel import get_tracer

active_routers: Dict[str, StatelessRouter] = {}
config: Optional[Config] = None
tracer = None
executor: Optional[ThreadPoolExecutor] = None

def load_rules(rules_path: str) -> RoutingRules:
    """Loads routing rules from a TOML file."""
    with open(rules_path, "r") as f:
        data = toml.load(f)
    
    agents = [AgentDefinition(**a) for a in data.get("agents", [])]
    global_rules = data.get("rules", {}).get("global_rules", [])
    
    return RoutingRules(agents=agents, global_rules=global_rules)

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
    global active_routers, config
    
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
        
        if config_path:
            parts = config_path.split('.')
            curr = config
            for p in parts:
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
            from origami_gemini.main import GeminiRouter
            builder.with_provider(GeminiRouter, config=config)
            active_routers[name] = builder.build()
                                    
        elif provider == "ember":
            from origami_ember.router import EmberRouter
            builder.with_provider(EmberRouter, config=config, **model_config)
            active_routers[name] = builder.build()

        elif provider == "auto_local":
            vllm_available = False
            try:
                from origami_vllm.main import VllmRouter, VllmRouterConfig
                vllm_available = True
            except (ImportError, ModuleNotFoundError):
                print(f"  vLLM not available for '{name}', checking for LlamaCpp...")

            try:
                from origami_llama_cpp.main import LlamaCppRouter, LlamaCppWorkerPool, LlamaCppRouterConfig
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
