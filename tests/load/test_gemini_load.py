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
from tests.data.data import RETAIL_TEST_CASES
from origami_common.otel import get_tracer

async def send_request(client, semaphore, results, tracer, base_url):
    """Sends a single routing request to the Gemini model."""
    async with semaphore:
        with tracer.start_as_current_span("load_test.gemini.send_request") as span:
            test_case = random.choice(RETAIL_TEST_CASES)
            prompt = test_case[0]
            expected = test_case[1]
            context_summary = test_case[2] if len(test_case) > 2 else None

            payload = {
                "model": "gemini",
                "prompt": prompt
            }
            
            has_context = False
            if context_summary:
                payload["context_summary"] = context_summary
                has_context = True
            
            span.set_attribute("test.prompt", prompt)
            span.set_attribute("test.context_used", has_context)
            try:
                response = await client.post(f"{base_url}/route", json=payload, timeout=30.0)
                success = response.status_code == 200
                results.append(success)
                span.set_attribute("http.status_code", response.status_code)
            except Exception as e:
                results.append(False)
                span.record_exception(e)
                span.set_status(status=2, description=str(e)) # 2 = ERROR

async def run_load_test(tracer, load_test_config):
    semaphore = asyncio.Semaphore(load_test_config["concurrent_clients"])
    results = []
    
    with tracer.start_as_current_span("load_test.gemini.execution_loop"):
        async with httpx.AsyncClient() as client:
            tasks = [send_request(client, semaphore, results, tracer, load_test_config["base_url"]) for _ in range(load_test_config["total_requests"])]
            await asyncio.gather(*tasks)
    
    return results

def test_gemini_load(load_test_config):
    """
    Executes a load test of 1000 requests against the Gemini Flash Lite router.
    Instrumented with OTel spans for trace analysis.
    """
    tracer = get_tracer("gemini_load_test")
    
    with tracer.start_as_current_span("gemini_load_test.total_execution") as parent_span:
        total_reqs = load_test_config["total_requests"]
        print(f"\nStarting GEMINI 3.1 FLASH LITE load test: {total_reqs} requests...")
        
        start_time = time.time()
        results = asyncio.run(run_load_test(tracer, load_test_config))
        end_time = time.time()
        
        duration = end_time - start_time
        success_count = sum(results)
        failure_count = total_reqs - success_count
        
        parent_span.set_attribute("test.total_requests", total_reqs)
        parent_span.set_attribute("test.success_count", success_count)
        parent_span.set_attribute("test.duration_seconds", duration)
        parent_span.set_attribute("test.rps", total_reqs / duration if duration > 0 else 0)
        
        print(f"\nGemini Load Test Results:")
        print(f"Total Requests: {total_reqs}")
        print(f"Successful: {success_count}")
        print(f"Failed: {failure_count}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Requests Per Second: {total_reqs / duration:.2f}" if duration > 0 else "N/A")

        # Allow for 5% failure rate in cloud/high-load scenarios
        assert success_count >= total_reqs * 0.95
