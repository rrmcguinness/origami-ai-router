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
from unittest.mock import MagicMock, patch
from stateless_router.models import RoutingRules
from gemini_router.main import GeminiRouter
from llama_cpp_router.main import LlamaCppRouter

@pytest.fixture
def mock_rules():
    return RoutingRules(agents=[{"name": "TestAgent", "description": "Test"}])

@pytest.mark.anyio
async def test_gemini_router_with_context(mock_rules):
    """Verifies that GeminiRouter correctly handles the context_summary argument."""
    with patch("google.genai.Client") as mock_client:
        router = GeminiRouter(rules=mock_rules)
        # Mock the generate_content call
        mock_response = MagicMock()
        mock_response.text = '{"route": "TestAgent"}'
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)
        mock_client.return_value.models.generate_content.return_value = mock_response
        
        # 1. Test without context
        await router.route("Hello")
        args, kwargs = mock_client.return_value.models.generate_content.call_args
        assert "User prompt: Hello" in kwargs["contents"]
        
        # 2. Test with context
        await router.route("Hello", context_summary="Previous context")
        args, kwargs = mock_client.return_value.models.generate_content.call_args
        assert "Reference Context: Previous context" in kwargs["contents"]
        assert "User prompt: Hello" in kwargs["contents"]

@pytest.mark.anyio
async def test_llama_cpp_router_with_context(mock_rules):
    """Verifies that LlamaCppRouter correctly handles the context_summary argument."""
    with patch("llama_cpp_router.main.Llama") as mock_llama:
        router = LlamaCppRouter(rules=mock_rules, model_path="mock.gguf")
        
        # Mock create_chat_completion
        mock_llama.return_value.create_chat_completion.return_value = {
            "choices": [{"message": {"content": '{"route": "TestAgent"}'}}]
        }
        
        # 1. Test without context
        await router.route("Hello")
        args, kwargs = mock_llama.return_value.create_chat_completion.call_args
        messages = kwargs["messages"]
        assert messages[1]["content"] == "User: Hello\nRoute:"
        
        # 2. Test with context
        await router.route("Hello", context_summary="Previous context")
        args, kwargs = mock_llama.return_value.create_chat_completion.call_args
        messages = kwargs["messages"]
        assert "Reference Context: Previous context" in messages[1]["content"]
        assert "User: Hello\nRoute:" in messages[1]["content"]
