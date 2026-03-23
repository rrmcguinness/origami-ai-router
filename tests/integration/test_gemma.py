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
from llama_cpp_router.main import LlamaCppRouter
from stateless_router.builder import RouterBuilder
from tests.integration.data import RETAIL_ROUTING_RULES, RETAIL_TEST_CASES, get_test_env_setting

@pytest.mark.anyio
@pytest.mark.parametrize("query,expected_route", RETAIL_TEST_CASES)
async def test_gemma_routing_load(query, expected_route, shared_executor):
    """
    Test routing over 20+ retail-specific agents using local Gemma driven by configuration.
    """
    model_path = get_test_env_setting("gemma_model_path")
    
    # Builder should handle the provider-specific initialization.
    router = (RouterBuilder()
              .with_executor(shared_executor)
              .with_rules(RETAIL_ROUTING_RULES)
              .with_provider(LlamaCppRouter, model_path=model_path)
              .build())
    
    assert isinstance(router, LlamaCppRouter)
    assert router.executor == shared_executor
    
    try:
        route = await router.route(query)
        # We allow for some model variance, but the outcome should be the expected route or Fallback
        assert route in [expected_route, "Fallback"], f"Gemma routed '{query}' to '{route}' but expected '{expected_route}'"
    except Exception as e:
        pytest.fail(f"Gemma routing failed for query '{query}': {e}")
