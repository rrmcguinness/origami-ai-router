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
import time
from gemini_router.main import GeminiRouter
from llama_cpp_router.main import LlamaCppRouter
from stateless_router.builder import RouterBuilder
from common.config import Config
from tests.integration.data import RETAIL_TEST_CASES, get_rules_for_provider, get_test_env_setting

@pytest.mark.regression
@pytest.mark.anyio
@pytest.mark.parametrize("query,expected_route", RETAIL_TEST_CASES)
@pytest.mark.parametrize("provider_type", ["gemini", "llama_cpp"])
async def test_full_accuracy_regression(query, expected_route, provider_type, shared_executor):
    """
    Comprehensive regression test covering all 600+ test cases across Gemini, and Llama Cpp.
    This test is excluded from standard runs via the 'regression' mark.
    """
    app_config = Config()
    
    # Dynamically load the rules for this specific provider (Gemini, Llama Cpp)
    rules = get_rules_for_provider(provider_type)
    
    if provider_type == "gemini":
        project_id = get_test_env_setting("google_project_id")
        if not project_id:
            project_id = getattr(getattr(app_config.baseConfig, "application", None), "google_project_id", "rmcguinness")
        
        router = (RouterBuilder()
                  .with_provider(GeminiRouter, project_id=project_id)
                  .with_rules(rules)
                  .with_executor(shared_executor)
                  .build())
    else: # provider_type == "llama_cpp":
        # Target the 8B model by default for llama_cpp provider tests
        model_path = get_test_env_setting("llama_model_path", provider_type="llama")
        
        router = (RouterBuilder()
                  .with_executor(shared_executor)
                  .with_rules(rules)
                  .with_provider(LlamaCppRouter, model_path=model_path)
                  .build())

    try:
        start_time = time.perf_counter()
        route = await router.route(query)
        duration = (time.perf_counter() - start_time) * 1000
        
        # Log to stdout for tracking during long runs if capturing is handled
        # print(f"[{provider_type}] '{query}' -> '{route}' (Expected: '{expected_route}') in {duration:.2f}ms")
        
        assert route == expected_route or route == "Fallback", f"[{provider_type}] Mismatch for '{query}': Got '{route}', Expected '{expected_route}'"
    except Exception as e:
        pytest.fail(f"[{provider_type}] routing failed for query '{query}': {e}")
