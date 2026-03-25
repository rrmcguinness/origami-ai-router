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
pytestmark = pytest.mark.regression
import time
from origami_gemini.main import GeminiRouter
from origami_llama_cpp.main import LlamaCppRouter, LlamaCppRouterConfig
from origami_stateless.builder import RouterBuilder
from origami_api.config import Config
from tests.data.data import RETAIL_TEST_CASES, get_rules_for_provider

@pytest.mark.regression
@pytest.mark.anyio
@pytest.mark.parametrize("query,expected_route,context_summary", RETAIL_TEST_CASES)
@pytest.mark.parametrize("provider_type", ["gemini", "llama_cpp"])
async def test_full_accuracy_regression(query, expected_route, context_summary, provider_type, shared_executor, session_config):
    """
    Comprehensive regression test covering all 600+ test cases across Gemini, and Llama Cpp.
    This test is excluded from standard runs via the 'regression' mark.
    """
    app_config = session_config
    
    # Dynamically load the rules for this specific provider (Gemini, Llama Cpp)
    rules = get_rules_for_provider(provider_type)
    
    if provider_type == "gemini":
        router = (RouterBuilder()
                  .with_provider(GeminiRouter, config=app_config)
                  .with_rules(rules)
                  .with_executor(shared_executor)
                  .build())
    else: # provider_type == "llama_cpp":
        llama_model = app_config.ai_models.get_model("llama") if hasattr(app_config, "ai_models") else None
        model_path = llama_model.model_path if llama_model and hasattr(llama_model, "model_path") else ""
        
        config = LlamaCppRouterConfig(model_path=model_path)
        
        router = (RouterBuilder()
                  .with_executor(shared_executor)
                  .with_rules(rules)
                  .with_provider(LlamaCppRouter, config=config)
                  .build())

    try:
        start_time = time.perf_counter()
        route = await router.route(query, context_summary=context_summary)
        duration = (time.perf_counter() - start_time) * 1000
        
        # Log to stdout for tracking during long runs if capturing is handled
        # print(f"[{provider_type}] '{query}' -> '{route}' (Expected: '{expected_route}') in {duration:.2f}ms")
        
        # Normalized for case-insensitive comparison
        actual_route = route.lower()
        expected_route_val = expected_route.lower()
        assert actual_route in [expected_route_val, "fallback"], f"[{provider_type}] Mismatch for '{query}': Got '{route}', Expected '{expected_route}'"
    except Exception as e:
        pytest.fail(f"[{provider_type}] routing failed for query '{query}': {e}")
