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
import time
import random
import threading
import uvicorn
import httpx
import asyncio
from edgerouter.main import app
from .data import RETAIL_TEST_CASES, get_test_env_setting
from common.otel import get_tracer, flush_otel

# Configuration for the load test driven by test_config.toml
SERVER_HOST = "127.0.0.1"
SERVER_PORT = int(get_test_env_setting("server_port_gemini", "8006"))
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
TOTAL_REQUESTS = int(get_test_env_setting("total_requests", "100"))
CONCURRENT_CLIENTS = int(get_test_env_setting("concurrent_clients", "10"))

def run_server():
    """Starts the FastAPI server in a separate thread."""
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, log_level="error")

@pytest.fixture(scope="module", autouse=True)
def engine_service():
    """Fixture to start and stop the server for the duration of the test module."""
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for server to be ready
    timeout = 15
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with httpx.Client() as client:
                response = client.get(f"{BASE_URL}/health")
                if response.status_code == 200:
                    break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        pytest.fail("Server failed to start in time for Gemini load test.")
    
    yield
    flush_otel()

async def send_request(client, semaphore, results, tracer):
    """Sends a single routing request to the Gemini model."""
    async with semaphore:
        with tracer.start_as_current_span("load_test.gemini.send_request") as span:
            prompt, expected = random.choice(RETAIL_TEST_CASES)
            payload = {
                "model": "gemini",
                "prompt": prompt
            }
            
            # Sampling: 25% chance of providing context_summary
            has_context = random.random() < 0.25
            if has_context:
                payload["context_summary"] = f"The user is currently asking about {expected}."
            
            span.set_attribute("test.prompt", prompt)
            span.set_attribute("test.context_used", has_context)
            try:
                response = await client.post(f"{BASE_URL}/route", json=payload, timeout=30.0)
                success = response.status_code == 200
                results.append(success)
                span.set_attribute("http.status_code", response.status_code)
            except Exception as e:
                results.append(False)
                span.record_exception(e)
                span.set_status(status=2, description=str(e)) # 2 = ERROR

async def run_load_test(tracer):
    semaphore = asyncio.Semaphore(CONCURRENT_CLIENTS)
    results = []
    
    with tracer.start_as_current_span("load_test.gemini.execution_loop"):
        async with httpx.AsyncClient() as client:
            tasks = [send_request(client, semaphore, results, tracer) for _ in range(TOTAL_REQUESTS)]
            await asyncio.gather(*tasks)
    
    return results

def test_gemini_load():
    """
    Executes a load test of 1000 requests against the Gemini Flash Lite router.
    Instrumented with OTel spans for trace analysis.
    """
    tracer = get_tracer("gemini_load_test")
    
    with tracer.start_as_current_span("gemini_load_test.total_execution") as parent_span:
        print(f"\nStarting GEMINI FLASH LITE load test: {TOTAL_REQUESTS} requests...")
        
        start_time = time.time()
        results = asyncio.run(run_load_test(tracer))
        end_time = time.time()
        
        duration = end_time - start_time
        success_count = sum(results)
        failure_count = TOTAL_REQUESTS - success_count
        
        parent_span.set_attribute("test.total_requests", TOTAL_REQUESTS)
        parent_span.set_attribute("test.success_count", success_count)
        parent_span.set_attribute("test.duration_seconds", duration)
        parent_span.set_attribute("test.rps", TOTAL_REQUESTS / duration)
        
        print(f"\nGemini Load Test Results:")
        print(f"Total Requests: {TOTAL_REQUESTS}")
        print(f"Successful: {success_count}")
        print(f"Failed: {failure_count}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Requests Per Second: {TOTAL_REQUESTS / duration:.2f}")

        # Allow for 5% failure rate in cloud/high-load scenarios
        assert success_count >= TOTAL_REQUESTS * 0.95
