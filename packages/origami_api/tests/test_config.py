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

import os
import pytest
from origami_api.config import Config, ENV_TOML

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
    assert config.server is not None
    assert config.ai_models is not None
    assert config.embeddings is not None

    assert config.application.location == "us-central1"
    assert config.application.name == "origami-router-unit"
    assert config.server.host == "0.0.0.0"
    assert config.server.port == 8000
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
    
    assert len(config.server.routers) == 3
    
    origami_gemini = config.server.get_router("gemini")
    assert origami_gemini is not None
    assert origami_gemini.provider == "gemini"
    assert origami_gemini.config_path == "gemini.flash"
    
    gemma_router = config.server.get_router("gemma")
    assert gemma_router is not None
    assert gemma_router.provider == "auto_local"
    assert gemma_router.n_threads == 4
