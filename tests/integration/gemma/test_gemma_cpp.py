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

import pytest
pytestmark = pytest.mark.integration
from origami_llama_cpp.main import LlamaCppRouter, LlamaCppRouterConfig
from origami_stateless.builder import RouterBuilder
from tests.data.data import RETAIL_ROUTING_RULES, RETAIL_TEST_CASES_SUBSET

@pytest.mark.anyio
@pytest.mark.parametrize("query,expected_route,context_summary", RETAIL_TEST_CASES_SUBSET[:25])
async def test_gemma_cpp_routing_load(query, expected_route, context_summary, shared_executor, session_config):
    """
    Test routing over 20+ retail-specific agents using local Gemma 3 weights driven by configuration.
    Uses LlamaCppRouter under the hood for local execution via llama-cpp-python.
    """
    
    model_path = session_config.server.get_router("gemma").model_path
    config = LlamaCppRouterConfig(model_path=model_path)
    
    # Builder should handle the provider-specific initialization.
    router = (RouterBuilder()
              .with_executor(shared_executor)
              .with_rules(RETAIL_ROUTING_RULES)
              .with_provider(LlamaCppRouter, config=config)
              .build())
    
    assert isinstance(router, LlamaCppRouter)
    assert router.executor == shared_executor
    
    try:
        route = await router.route(query, context_summary=context_summary)
        # We allow for some model variance, but the outcome should be the expected route or Fallback
        actual_route = route.lower().strip()
        expected_route_val = expected_route.lower().strip()
        assert actual_route in [expected_route_val, "fallback"], f"Gemma routed '{query}' to '{actual_route!r}' but expected '{expected_route_val!r}'"
    except Exception as e:
        pytest.fail(f"Gemma routing failed for query '{query}': {e}")
