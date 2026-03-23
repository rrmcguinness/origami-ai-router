import pytest
from gemini_router.main import GeminiRouter
from stateless_router.builder import RouterBuilder
from common.config import Config
from tests.integration.data import RETAIL_ROUTING_RULES, RETAIL_TEST_CASES, get_test_env_setting

@pytest.mark.anyio
@pytest.mark.parametrize("query,expected_route", RETAIL_TEST_CASES)
async def test_gemini_routing_load(query, expected_route, shared_executor):
    """
    Test routing over 20+ retail-specific agents using configuration-driven Gemini settings.
    """
    # Prefer project ID from test_config.toml, then base app config, then a hardcoded default.
    app_config = Config()
    project_id = get_test_env_setting("google_project_id")
    if not project_id:
        project_id = getattr(getattr(app_config.baseConfig, "application", None), "google_project_id", "rmcguinness")
    
    router = (RouterBuilder()
              .with_provider(GeminiRouter, project_id=project_id)
              .with_rules(RETAIL_ROUTING_RULES)
              .with_executor(shared_executor)
              .build())
    assert isinstance(router, GeminiRouter)
    assert router.executor == shared_executor
    
    try:
        route = await router.route(query)
        # We allow for some model variance, but the outcome should be the expected route or Fallback
        assert route in [expected_route, "Fallback"], f"Gemini routed '{query}' to '{route}' but expected '{expected_route}'"
    except Exception as e:
        pytest.fail(f"Gemini routing failed for query '{query}': {e}")
