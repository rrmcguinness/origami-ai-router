import pytest
from stateless_router.builder import RouterBuilder
from stateless_router.models import RoutingRules, AgentDefinition
from stateless_router.interface import StatelessRouter

class MockRouter(StatelessRouter):
    """Simple mock router for unit testing the builder."""
    def __init__(self, rules: RoutingRules, **kwargs):
        super().__init__(rules)
        self.kwargs = kwargs

    def route(self, user_query: str) -> str:
        return "MockedRoute"

def test_router_builder_success():
    rules = RoutingRules(
        agents=[
            AgentDefinition(name="TestAgent", description="A test agent.")
        ]
    )
    
    builder = RouterBuilder()
    router = (builder
              .with_provider(MockRouter, custom_arg="special_value")
              .with_rules(rules)
              .build())
    
    assert isinstance(router, MockRouter)
    assert router.rules == rules
    assert router.kwargs["custom_arg"] == "special_value"
    assert router.route("any query") == "MockedRoute"

def test_router_builder_missing_rules():
    builder = RouterBuilder()
    builder.with_provider(MockRouter)
    
    with pytest.raises(ValueError, match="Provide a RoutingRules object"):
        builder.build()

def test_router_builder_missing_provider():
    rules = RoutingRules(agents=[AgentDefinition(name="A", description="B")])
    builder = RouterBuilder()
    builder.with_rules(rules)
    
    with pytest.raises(ValueError, match="forgot to provide a router implementation"):
        builder.build()
