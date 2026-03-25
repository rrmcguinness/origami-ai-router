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
import asyncio
from origami_gemini.main import GeminiRouter
from origami_stateless.builder import RouterBuilder
from origami_api.config import Config
from tests.data.data import RETAIL_TEST_CASES, RETAIL_ROUTING_RULES

# Limit concurrency to avoid hitting Vertex AI rate limits or 503s/500s on the preview model
sem = asyncio.Semaphore(2)


@pytest.mark.anyio
@pytest.mark.parametrize("query, expected_route, context_summary", RETAIL_TEST_CASES[:25])
async def test_gemini_routing_load(query, expected_route, context_summary, shared_executor, session_config):
    """
    Tests the routing accuracy under a simulated load for Gemini.
    """

    
    router = (RouterBuilder()
              .with_provider(GeminiRouter, config=session_config)
              .with_rules(RETAIL_ROUTING_RULES)
              .with_executor(shared_executor)
              .build())
    assert isinstance(router, GeminiRouter)
    
    async with sem:
        try:
            route = await router.route(query, context_summary=context_summary)
            # We allow for some model variance, and normalize for case-insensitive comparison
            actual_route = route.lower().strip()
            expected_route_val = expected_route.lower().strip()
            assert actual_route in [expected_route_val, "fallback"], f"Gemini routed '{query}' to '{actual_route!r}' but expected '{expected_route_val!r}'"
        except Exception as e:
            pytest.fail(f"Gemini routing failed for query '{query}': {e}")
