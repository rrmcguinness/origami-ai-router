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
import httpx
import asyncio
import time
import subprocess
import os
from common.otel import flush_otel

BASE_URL = "http://127.0.0.1:8000"

@pytest.fixture(scope="module", autouse=True)
def setup_server():
    """Starts the EdgeRouter server for testing."""
    env = os.environ.copy()
    env["PYTHONPATH"] = "src:packages/common/src:packages/stateless_router/src:packages/gemini_router/src:packages/vllm_router/src:packages/llama_cpp_router/src"
    
    server_process = subprocess.Popen(
        [".venv/bin/python", "-m", "src.edgerouter.main", "--rules", "rules.toml"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for server to start
    timeout = 30
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with httpx.Client() as client:
                response = client.get(f"{BASE_URL}/health")
                if response.status_code == 200:
                    break
        except Exception:
            pass
        time.sleep(1.0)
    else:
        server_process.kill()
        pytest.fail("Server failed to start in time for context summary test.")
    
    yield
    server_process.kill()
    flush_otel()

@pytest.mark.anyio
async def test_context_summary_routing():
    """Verifies that the API correctly handles the optional context_summary field."""
    async with httpx.AsyncClient() as client:
        # 1. Test without context_summary (baseline)
        payload_no_ctx = {
            "model": "gemini",
            "prompt": "I need help with my medication."
        }
        response = await client.post(f"{BASE_URL}/route", json=payload_no_ctx)
        assert response.status_code == 200
        assert "route" in response.json()

        # 2. Test with context_summary
        payload_with_ctx = {
            "model": "gemini",
            "prompt": "Tell me more about the dosage.",
            "context_summary": "The user is currently asking about their heart medication Lisinopril."
        }
        response = await client.post(f"{BASE_URL}/route", json=payload_with_ctx)
        assert response.status_code == 200
        assert "route" in response.json()
        
        # We can't easily verify the *output* change without a mock router, 
        # but we've verified the API contract at least.
