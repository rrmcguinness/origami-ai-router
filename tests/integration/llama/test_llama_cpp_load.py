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
import httpx
import asyncio
from edgerouter.main import app
from .data import RETAIL_TEST_CASES, get_test_env_setting
from common.otel import get_tracer, flush_otel
from common.config import Config

from opentelemetry.propagate import inject

TOTAL_REQUESTS = int(get_test_env_setting("total_requests", "100"))
CONCURRENT_CLIENTS = int(get_test_env_setting("concurrent_clients", "10"))

@pytest.fixture(scope="module", autouse=True)
def otel_flush():
    """Fixture to flush the OTEL telemetry at the end of the module."""
    yield
    flush_otel()

async def send_request(client, semaphore, results, tracer, target_model: str):
    """Sends a single routing request with a random test case."""
    async with semaphore:
        with tracer.start_as_current_span("load_test.send_request") as span:
            prompt, expected = random.choice(RETAIL_TEST_CASES)
            payload = {
                "model": target_model,
                "prompt": prompt
            }
            
            # Sampling: 25% chance of providing context_summary
            has_context = random.random() < 0.25
            if has_context:
                payload["context_summary"] = f"The user is currently asking about {expected}."
                
            span.set_attribute("test.prompt", prompt)
            span.set_attribute("test.context_used", has_context)
            
            headers = {}
            inject(headers)
            
            try:
                response = await client.post("http://test/route", json=payload, headers=headers, timeout=30.0)
                success = response.status_code == 200
                results.append(success)
                span.set_attribute("http.status_code", response.status_code)
            except Exception as e:
                results.append(False)
                span.record_exception(e)
                span.set_status(status=2, description=str(e)) # 2 = ERROR

async def run_load_test(tracer, target_model: str):
    semaphore = asyncio.Semaphore(CONCURRENT_CLIENTS)
    results = []
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        print(f"Warming up Local AI Router (LlamaCpp) for model '{target_model}'...")
        await client.post("http://test/route", json={"model": target_model, "prompt": "warmup"}, timeout=120.0)
        print("Warmup complete. Starting load generation.")
        
        start_time = time.time()
        with tracer.start_as_current_span("load_test.execution_loop"):
            tasks = [send_request(client, semaphore, results, tracer, target_model) for _ in range(TOTAL_REQUESTS)]
            await asyncio.gather(*tasks)
        end_time = time.time()
        
    return results, start_time, end_time

def test_llama_cpp_load():
    """
    Executes a load test against the LlamaCpp (formerly Gemma) router.
    Uses asyncio to ensure concurrent execution from the client side.
    Instrumented with OTel spans for trace analysis.
    """
    tracer = get_tracer("local_router_load_test")
    
    with tracer.start_as_current_span("local_router_load_test.total_execution") as parent_span:
        cfg = Config()
        test_cfg = getattr(cfg.baseConfig, "test", None)
        target_model = getattr(test_cfg, "model", "llama")
        
        print(f"\nStarting INSTRUMENTED ASYNC load test for LlamaCpp model '{target_model}': {TOTAL_REQUESTS} requests...")
        
        results, start_time, end_time = asyncio.run(run_load_test(tracer, target_model))
        
        duration = end_time - start_time
        success_count = sum(results)
        failure_count = TOTAL_REQUESTS - success_count
        
        parent_span.set_attribute("test.total_requests", TOTAL_REQUESTS)
        parent_span.set_attribute("test.success_count", success_count)
        parent_span.set_attribute("test.duration_seconds", duration)
        parent_span.set_attribute("test.rps", TOTAL_REQUESTS / duration)
        
        print(f"\nAsync Load Test Results:")
        print(f"Total Requests: {TOTAL_REQUESTS}")
        print(f"Successful: {success_count}")
        print(f"Failed: {failure_count}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Requests Per Second: {TOTAL_REQUESTS / duration:.2f}")

        # Allow for 5% failure rate in high-load scenarios
        assert success_count >= TOTAL_REQUESTS * 0.95
