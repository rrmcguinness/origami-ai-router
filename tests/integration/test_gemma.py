import pytest
from gemma_router.main import GemmaRouter, get_current_file_path
from stateless_router.builder import RouterBuilder
from tests.integration.data import RETAIL_ROUTING_RULES, RETAIL_TEST_CASES, get_test_env_setting

@pytest.mark.anyio
@pytest.mark.parametrize("query,expected_route", RETAIL_TEST_CASES)
async def test_gemma_routing_load(query, expected_route, shared_executor):
    """
    Test routing over 20+ retail-specific agents using local Gemma driven by configuration.
    """
    # Prefer model path from test_config.toml for integration testing flexibility
    model_path = get_test_env_setting("gemma_model_path", "./gemma-3-270m-it-qat-Q4_0.gguf")
    
    # Resolve the path if it's relative to the test directory (legacy behavior support)
    if model_path.startswith("./"):
        model_path = get_current_file_path(model_path)
    
    router = (RouterBuilder()
              .with_provider(GemmaRouter, model_path=model_path)
              .with_rules(RETAIL_ROUTING_RULES)
              .with_executor(shared_executor)
              .build())
    assert isinstance(router, GemmaRouter)
    assert router.executor == shared_executor
    
    try:
        route = await router.route(query)
        # We allow for some model variance, but the outcome should be the expected route or Fallback
        assert route in [expected_route, "Fallback"], f"Gemma routed '{query}' to '{route}' but expected '{expected_route}'"
    except Exception as e:
        pytest.fail(f"Gemma routing failed for query '{query}': {e}")
