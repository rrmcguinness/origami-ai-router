import os
import pytest
from edgerouter_api.config import Config, ENV_TOML

from unittest.mock import patch

def test_config_override():
    os.environ["RUNTIME_ENV"] = "unit"
    
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    env_file_path = os.path.join(workspace_root, ENV_TOML)
    
    # Mock os.path.isfile to return False for .env.local.toml so it doesn't pollute the test
    original_isfile = os.path.isfile
    def mock_isfile(path):
        if path.endswith(".env.local.toml"):
            return False
        return original_isfile(path)
        
    with patch("os.path.isfile", side_effect=mock_isfile):
        config = Config(env_file_path)

    assert config is not None

    assert config.application is not None
    assert config.api_server is not None
    assert config.ai_models is not None
    assert config.embeddings is not None

    assert config.application.location == "us-central1"
    assert config.application.name == "edge-router-test"
    assert config.api_server.host == "0.0.0.0"
    assert config.api_server.port == 8000
    assert config.ai_models.router.model_name == "gemini-3.1-flash-lite-preview"
    assert config.ai_models.router.temperature == 1.0
    assert config.ai_models.router.top_p == 0.5
    assert config.ai_models.router.top_k == 40
    assert config.ai_models.router.output_format == "application/json"
    assert config.ai_models.router.max_tokens == 32000
    assert config.ai_models.router.api_key == "[ENCRYPTION_KEY]"
    assert config.ai_models.router.instructions == "## Purpose\nA purpose built router for edge services.\n"
    assert config.ai_models.embeddings.model_name == "text-embedding-004"
    assert config.ai_models.embeddings.api_key == ""
    assert config.ai_models.embeddings.instructions == "## Purpose\nA purpose built router for edge services.\n"
    
    assert len(config.api_server.routers) == 3
    
    gemini_router = config.api_server.get_router("gemini")
    assert gemini_router is not None
    assert gemini_router.provider == "gemini"
    assert gemini_router.config_path == "gemini.flash"
    
    gemma_router = config.api_server.get_router("gemma")
    assert gemma_router is not None
    assert gemma_router.provider == "auto_local"
    assert gemma_router.n_threads == 4
