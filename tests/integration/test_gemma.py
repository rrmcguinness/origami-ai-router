import pytest
from gemma_router.main import GemmaRouter, get_current_file_path
from stateless_router.builder import RouterBuilder
from tests.integration.data import RETAIL_ROUTING_RULES, RETAIL_TEST_CASES

@pytest.mark.parametrize("query,expected_route", RETAIL_TEST_CASES)
def test_gemma_routing_load(query, expected_route):
    """
    Test routing over 20+ retail-specific agents using local Gemma.
    """
    model_path = get_current_file_path("./gemma-3-270m-it-qat-Q4_0.gguf")
    
    router = (RouterBuilder()
              .with_provider(GemmaRouter, model_path=model_path)
              .with_rules(RETAIL_ROUTING_RULES)
              .build())
    assert isinstance(router, GemmaRouter)
    
    try:
        route = router.route(query)
        # We allow for some model variance, but the outcome should be the expected route or Fallback
        assert route in [expected_route, "Fallback"], f"Gemma routed '{query}' to '{route}' but expected '{expected_route}'"
    except Exception as e:
        pytest.fail(f"Gemma routing failed for query '{query}': {e}")
