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
from common.config import Config
from stateless_router.models import RoutingRules, AgentDefinition

# Load test configuration paths
_base_dir = os.path.dirname(__file__)
_test_cases_path = os.path.join(_base_dir, "test_cases.toml")

# Dynamically construct Test Cases from the shared configuration
_cases_config = Config(file=_test_cases_path)
RETAIL_TEST_CASES = [tuple(case) for case in _cases_config.baseConfig.tests.cases]
RETAIL_TEST_CASES_SUBSET = RETAIL_TEST_CASES[:100]

def get_rules_for_provider(provider_type: str) -> RoutingRules:
    """
    Dynamically loads the specialized routing rules for a given provider.
    """
    if "gemini" in provider_type.lower():
        config_file = "test_config_gemini.toml"
    elif "gemma" in provider_type.lower() or "llama" in provider_type.lower():
        config_file = "test_config_llama_cpp.toml"
    elif "vllm" in provider_type.lower():
        config_file = "test_config_vllm.toml"
    else:
        config_file = "test_config.toml"
        
    path = os.path.join(_base_dir, config_file)
    if not os.path.exists(path):
        path = os.path.join(_base_dir, "test_config.toml")
        
    config = Config(file=path)
    
    # Extract global rules from the routing section if present
    global_rules = getattr(config.baseConfig.routing, "global_rules", [])
    if isinstance(global_rules, str):
        global_rules = [global_rules]

    return RoutingRules(
        agents=[
            AgentDefinition(
                name=agent["name"] if isinstance(agent, dict) else agent.name,
                description=agent["description"] if isinstance(agent, dict) else agent.description,
                instructions=agent.get("instructions") if isinstance(agent, dict) else getattr(agent, "instructions", None),
                salience=agent.get("salience", 0) if isinstance(agent, dict) else getattr(agent, "salience", 0)
            )
            for agent in config.baseConfig.routing.agents
        ],
        global_rules=global_rules
    )

# Legacy support (defaults to Gemini rules for global variable)
RETAIL_ROUTING_RULES = get_rules_for_provider("gemini")

def get_test_env_setting(key: str, default: str = None, provider_type: str = None) -> str:
    # Use the provider-specific config if available, otherwise fallback to base
    config_file = "test_config.toml"
    if provider_type:
        if "gemini" in provider_type.lower():
            config_file = "test_config_gemini.toml"
        elif "gemma" in provider_type.lower() or "llama" in provider_type.lower():
            config_file = "test_config_llama_cpp.toml"
            
    path = os.path.join(_base_dir, config_file)
    if not os.path.exists(path):
        path = os.path.join(_base_dir, "test_config.toml")
        
    config = Config(file=path)
    val = getattr(config.baseConfig.environment, key, None)
    if val is not None:
        return val
    return getattr(config.baseConfig.load_test, key, default)
