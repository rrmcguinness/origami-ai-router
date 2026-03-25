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
from llama_cpp_router.main import LlamaCppRouter, LlamaCppRouterConfig
from stateless_router.builder import RouterBuilder
from tests.integration.data import RETAIL_ROUTING_RULES, RETAIL_TEST_CASES_SUBSET, get_test_env_setting

@pytest.mark.anyio
@pytest.mark.parametrize("query,expected_route,context_summary", RETAIL_TEST_CASES_SUBSET)
async def test_llama_cpp_routing_load(query, expected_route, context_summary, shared_executor):
    """
    Test routing over 20+ retail-specific agents using local LlamaCpp driven by configuration.
    """
    # Use the universal llama_cpp config to resolve the current model path
    model_path = get_test_env_setting("llama_model_path", provider_type="llama")
    
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
        assert route in [expected_route, "Fallback"], f"LlamaCpp routed '{query}' to '{route}' but expected '{expected_route}'"
    except Exception as e:
        pytest.fail(f"LlamaCpp routing failed for query '{query}': {e}")
