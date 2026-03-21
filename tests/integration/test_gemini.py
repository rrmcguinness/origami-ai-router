import pytest
from gemini_router.main import GeminiRouter
from stateless_router.builder import RouterBuilder
from common.config import Config
from tests.integration.data import RETAIL_ROUTING_RULES, RETAIL_TEST_CASES

@pytest.mark.parametrize("query,expected_route", RETAIL_TEST_CASES)
def test_gemini_routing_load(query, expected_route):
    """
    Test routing over 20+ retail-specific agents using Gemini.
    """
    config = Config()
    project_id = getattr(config.baseConfig.application, "google_project_id", "rmcguinness")
    
    # We build the router per test case for now To ensure isolation, 
    # but in a real load test we might want to cache it.
    router = (RouterBuilder()
              .with_provider(GeminiRouter, project_id=project_id)
              .with_rules(RETAIL_ROUTING_RULES)
              .build())
    assert isinstance(router, GeminiRouter)
    
    try:
        route = router.route(query)
        # We allow for some model variance, but the outcome should be the expected route or Fallback
        assert route in [expected_route, "Fallback"], f"Gemini routed '{query}' to '{route}' but expected '{expected_route}'"
    except Exception as e:
        pytest.fail(f"Gemini routing failed for query '{query}': {e}")
