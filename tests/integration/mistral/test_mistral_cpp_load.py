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
from tests.integration.data import RETAIL_TEST_CASES, get_test_env_setting
from common.otel import get_tracer, flush_otel

from opentelemetry.propagate import inject

TOTAL_REQUESTS = int(get_test_env_setting("total_requests", "100", "mistral"))
CONCURRENT_CLIENTS = int(get_test_env_setting("concurrent_clients", "10", "mistral"))

@pytest.fixture(scope="module", autouse=True)
def otel_flush():
    yield
    flush_otel()

async def send_request(client, semaphore, results, tracer, target_model: str):
    async with semaphore:
        with tracer.start_as_current_span("load_test.send_request") as span:
            test_case = random.choice(RETAIL_TEST_CASES)
            prompt = test_case[0]
            expected = test_case[1]
            context_summary = test_case[2] if len(test_case) > 2 else None
            
            payload = {
                "model": target_model,
                "prompt": prompt
            }
            if context_summary:
                payload["context_summary"] = context_summary
            
            headers = {}
            inject(headers)
            
            try:
                response = await client.post("http://test/route", json=payload, headers=headers, timeout=30.0)
                success = response.status_code == 200
                if success:
                    route = response.json().get("route")
                    if route != expected:
                        print(f"Accuracy failure: Expected '{expected}', Got '{route}' for prompt: '{prompt}'")
                        success = False
                else:
                    print(f"Failed request! Status: {response.status_code}, Body: {response.text}")
                results.append(success)
            except Exception as e:
                print(f"Exception during request: {e}")
                results.append(False)

async def run_load_test(tracer, target_model: str):
    semaphore = asyncio.Semaphore(CONCURRENT_CLIENTS)
    results = []
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        print(f"Warming up Local AI Router (Mistral) for model '{target_model}'...")
        await client.post("http://test/route", json={"model": target_model, "prompt": "warmup"}, timeout=120.0)
        print("Warmup complete. Starting load generation.")
        
        start_time = time.time()
        with tracer.start_as_current_span("load_test.execution_loop"):
            tasks = [send_request(client, semaphore, results, tracer, target_model) for _ in range(TOTAL_REQUESTS)]
            await asyncio.gather(*tasks)
        end_time = time.time()
        
    return results, start_time, end_time

def test_mistral_cpp_load():
    tracer = get_tracer("local_router_load_test")
    
    with tracer.start_as_current_span("local_router_load_test.total_execution") as parent_span:
        from edgerouter_api.config import Config
        cfg = Config()
        target_model = "mistral"
        
        print(f"\nStarting INSTRUMENTED ASYNC load test for Mistral model '{target_model}': {TOTAL_REQUESTS} requests...")
        
        results, start_time, end_time = asyncio.run(run_load_test(tracer, target_model))
        
        duration = end_time - start_time
        success_count = sum(results)
        failure_count = TOTAL_REQUESTS - success_count
        
        parent_span.set_attribute("test.rps", TOTAL_REQUESTS / duration)
        
        print(f"\nAsync Load Test Results:")
        print(f"Total Requests: {TOTAL_REQUESTS}")
        print(f"Successful: {success_count}")
        print(f"Failed: {failure_count}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Requests Per Second: {TOTAL_REQUESTS / duration:.2f}")

        assert success_count >= TOTAL_REQUESTS * 0.95
