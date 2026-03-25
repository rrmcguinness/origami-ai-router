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
import tomllib
from origami_api.config import Config
from origami_api.models import RoutingRules, AgentDefinition

# Load test configuration paths
_base_dir = os.path.dirname(__file__)
_test_cases_path = os.path.join(_base_dir, "test_cases.toml")

with open(_test_cases_path, "rb") as f:
    _tests_data = tomllib.load(f)

RETAIL_TEST_CASES = []
for case in _tests_data.get("tests", {}).get("cases", []):
    if len(case) == 3:
        RETAIL_TEST_CASES.append((case[0], case[1], case[2]))
    else:
        RETAIL_TEST_CASES.append((case[0], case[1], None))

RETAIL_TEST_CASES_SUBSET = RETAIL_TEST_CASES[:100]

def load_hierarchical_data(provider_type: str = None) -> dict:
    base_path = os.path.join(_base_dir, "test_config.toml")
    with open(base_path, "rb") as f:
        data = tomllib.load(f)
        
    config_file = None
    if provider_type:
        if "gemini" in provider_type.lower():
            config_file = "gemini/test_config_gemini.toml"
        elif "gemma" in provider_type.lower() or "llama" in provider_type.lower():
            config_file = "llama/test_config_llama_cpp.toml"
        elif "vllm" in provider_type.lower():
            config_file = "vllm/test_config_vllm.toml"
            
    if config_file:
        override_path = os.path.join(_base_dir, config_file)
        if os.path.exists(override_path):
            with open(override_path, "rb") as f:
                override_data = tomllib.load(f)
            
            def deep_merge(d1, d2):
                for k, v in d2.items():
                    if isinstance(v, dict) and k in d1 and isinstance(d1[k], dict):
                        deep_merge(d1[k], v)
                    else:
                        d1[k] = v
                return d1
                
            data = deep_merge(data, override_data)
            
    return data

def get_rules_for_provider(provider_type: str) -> RoutingRules:
    """
    Dynamically loads the specialized routing rules for a given provider.
    """
    cfg = Config()
    rules_file = getattr(cfg.application, "rules_file", "rules.toml")
    project_root = os.path.abspath(os.path.join(_base_dir, "..", ".."))
    rules_path = os.path.join(project_root, rules_file)
    
    if not os.path.exists(rules_path):
        rules_path = rules_file
        
    with open(rules_path, "rb") as f:
        app_rules_data = tomllib.load(f)
        
    agents_data = app_rules_data.get("agents", [])
    rules_data = app_rules_data.get("rules", {})
    global_rules = rules_data.get("global_rules", [])
    if isinstance(global_rules, str):
        global_rules = [global_rules]

    return RoutingRules(
        agents=[
            AgentDefinition(
                name=agent.get("name"),
                description=agent.get("description"),
                instructions=agent.get("instructions"),
                salience=agent.get("salience", 0)
            )
            for agent in agents_data
        ],
        global_rules=global_rules
    )

# Legacy support (defaults to Gemini rules for global variable)
RETAIL_ROUTING_RULES = get_rules_for_provider("gemini")
