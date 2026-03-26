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
pytestmark = pytest.mark.load
import time
import random
import httpx
import asyncio
from origami_router.main import app
from tests.data.data import RETAIL_TEST_CASES
from origami_common.otel import get_tracer, flush_otel

from opentelemetry.propagate import inject

@pytest.fixture(scope="module", autouse=True)
def otel_flush():
    """Fixture to flush the OTEL telemetry at the end of the module."""
    yield
    flush_otel()

async def send_request(client, semaphore, results, tracer, target_model: str):
    """Sends a single routing request with a random test case."""
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
            
            has_context = False
            if context_summary:
                payload["context_summary"] = context_summary
                has_context = True
                
            span.set_attribute("test.prompt", prompt)
            span.set_attribute("test.context_used", has_context)
            
            headers = {}
            inject(headers)
            
            try:
                response = await client.post("http://test/route", json=payload, headers=headers, timeout=30.0)
                success = response.status_code == 200
                is_accurate = False
                
                if success:
                    route = response.json().get("route")
                    if route == expected:
                        is_accurate = True
                    else:
                        # Log inaccurate predictions for analysis, but don't spam stdout during heavy load
                        # print(f"Accuracy failure: Expected '{expected}', Got '{route}' for prompt: '{prompt}'")
                        success = False
                        
                if not success and response.status_code != 200:
                    print(f"Failed request! Status: {response.status_code}, Body: {response.text}")
                
                # We return a tuple: (was_http_200, was_accurate)
                results.append((response.status_code == 200, is_accurate))
                span.set_attribute("http.status_code", response.status_code)
            except Exception as e:
                print(f"Exception during request: {e}")
                results.append((False, False))
                span.record_exception(e)
                span.set_status(status=2, description=str(e)) # 2 = ERROR

async def run_load_test(tracer, target_model: str, load_test_config):
    semaphore = asyncio.Semaphore(load_test_config["concurrent_clients"])
    results = []
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        print(f"Warming up Ember Router for model '{target_model}'...")
        await client.post("http://test/route", json={"model": target_model, "prompt": "warmup"}, timeout=120.0)
        print("Warmup complete. Starting load generation.")
        
        start_time = time.time()
        with tracer.start_as_current_span("load_test.execution_loop"):
            tasks = [send_request(client, semaphore, results, tracer, target_model) for _ in range(load_test_config["total_requests"])]
            await asyncio.gather(*tasks)
        end_time = time.time()
        
    return results, start_time, end_time

def test_ember_load(load_test_config):
    """
    Executes a load test against the Ember router and evaluates accuracy.
    """
    tracer = get_tracer("local_router_load_test")
    
    with tracer.start_as_current_span("local_router_load_test.total_execution") as parent_span:
        target_model = "ember"
        total_requests = load_test_config["total_requests"]
        
        print(f"\nStarting INSTRUMENTED ASYNC load test for Ember model '{target_model}': {total_requests} requests...")
        
        results, start_time, end_time = asyncio.run(run_load_test(tracer, target_model, load_test_config))
        
        duration = end_time - start_time
        
        # results is a list of (http_success, is_accurate) tuples
        successful_requests = sum(1 for r in results if r[0])
        accurate_predictions = sum(1 for r in results if r[1])
        
        failure_count = total_requests - successful_requests
        
        # Accuracy is based on requests that actually completed successfully
        accuracy_percent = (accurate_predictions / successful_requests * 100) if successful_requests > 0 else 0.0
        
        parent_span.set_attribute("test.total_requests", total_requests)
        parent_span.set_attribute("test.success_count", successful_requests)
        parent_span.set_attribute("test.duration_seconds", duration)
        parent_span.set_attribute("test.rps", total_requests / duration)
        
        print(f"\n==========================================")
        print(f"Ember Router (BGE-M3) Load Test Results:")
        print(f"==========================================")
        print(f"Total Requests: {total_requests}")
        print(f"HTTP Successful: {successful_requests}")
        print(f"HTTP Failed: {failure_count}")
        print(f"Correctly Routed: {accurate_predictions}")
        print(f"Accuracy Rate: {accuracy_percent:.2f}%")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Requests Per Second (RPS): {total_requests / duration:.2f}")
        print(f"==========================================")

        # Basic assertion that the router didn't completely fall over
        assert successful_requests >= total_requests * 0.95, "HTTP Error rate too high"
        
        # We don't strictly assert a high accuracy because BGE-M3 is a smaller embedding model,
        # but it gives us a baseline to look at. We can assert it's better than random chance (1/11 ~ 9%).
        assert accuracy_percent >= 15.0, f"Accuracy too low ({accuracy_percent}%) for an embedding router"
