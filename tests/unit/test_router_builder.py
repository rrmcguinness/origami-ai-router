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
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from stateless_router.builder import RouterBuilder
from edgerouter_api.models import RoutingRules, AgentDefinition
from edgerouter_api.interfaces import StatelessRouter
from edgerouter_api.config import RouterConfig

class MockConfig(RouterConfig):
    pass

class MockRouter(StatelessRouter):
    """Simple mock router for unit testing the builder."""
    def __init__(self, rules: RoutingRules, config: RouterConfig, executor: Optional[ThreadPoolExecutor] = None, **kwargs):
        super().__init__(rules=rules, config=config, executor=executor, **kwargs)
        self.kwargs = kwargs

    async def route(self, user_query: str) -> str:
        return "MockedRoute"

@pytest.mark.anyio
async def test_router_builder_success(shared_executor):
    rules = RoutingRules(
        agents=[
            AgentDefinition(name="TestAgent", description="A test agent.")
        ]
    )
    
    builder = RouterBuilder()
    router = (builder
              .with_provider(MockRouter, config=MockConfig(), custom_arg="special_value")
              .with_rules(rules)
              .with_executor(shared_executor)
              .build())
    
    assert isinstance(router, MockRouter)
    assert router.rules == rules
    assert router.executor == shared_executor
    assert router.kwargs["custom_arg"] == "special_value"
    assert await router.route("any query") == "MockedRoute"

@pytest.mark.anyio
async def test_router_builder_missing_rules():
    builder = RouterBuilder()
    builder.with_provider(MockRouter, config=MockConfig())
    
    with pytest.raises(ValueError, match="Provide a RoutingRules object"):
        builder.build()

@pytest.mark.anyio
async def test_router_builder_missing_config():
    rules = RoutingRules(agents=[AgentDefinition(name="A", description="B")])
    builder = RouterBuilder()
    builder.with_rules(rules)
    builder._router_class = MockRouter
    
    with pytest.raises(ValueError, match="A valid RouterConfig object must be provided."):
        builder.build()

@pytest.mark.anyio
async def test_router_builder_missing_provider():
    rules = RoutingRules(agents=[AgentDefinition(name="A", description="B")])
    builder = RouterBuilder()
    builder.with_rules(rules)
    
    with pytest.raises(ValueError, match="forgot to provide a router implementation"):
        builder.build()
