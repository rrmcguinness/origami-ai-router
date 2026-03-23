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

# Load test configuration from the local TOML file
# This drives the integration tests with structured data instead of hardcoded constants.
_test_config_path = os.path.join(os.path.dirname(__file__), "test_config.toml")
_config = Config(file=_test_config_path)

# Dynamically construct RoutingRules from configuration
RETAIL_ROUTING_RULES = RoutingRules(
    agents=[
        AgentDefinition(**agent) if isinstance(agent, dict) else AgentDefinition(name=agent.name, description=agent.description)
        for agent in _config.baseConfig.routing.agents
    ]
)

# Dynamically construct Test Cases from configuration
# We convert the list of lists from TOML into a list of tuples for pytest.mark.parametrize
RETAIL_TEST_CASES = [tuple(case) for case in _config.baseConfig.tests.cases]

# Helper to get environment-specific test settings
def get_test_env_setting(key: str, default: str = None) -> str:
    # Check [environment] section first
    val = getattr(_config.baseConfig.environment, key, None)
    if val is not None:
        return val
    # Fallback to [load_test] section
    return getattr(_config.baseConfig.load_test, key, default)
