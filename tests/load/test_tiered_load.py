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

@pytest.fixture(scope="module", autouse=True)
def otel_flush():
    yield
    flush_otel()

async def send_request(client, semaphore, results, target_model: str):
    async with semaphore:
        test_case = random.choice(RETAIL_TEST_CASES)
        prompt = test_case[0]
        expected = test_case[1]
        
        try:
            start = time.time()
            response = await client.post("http://test/route", json={"model": target_model, "prompt": prompt}, timeout=120.0)
            latency = time.time() - start
            
            success = response.status_code == 200
            is_accurate = False
            if success:
                route = response.json().get("route")
                is_accurate = (route == expected)
            
            results.append({
                "success": success,
                "accurate": is_accurate,
                "latency": latency
            })
        except Exception as e:
            print(f"Request failed: {e}")
            results.append({"success": False, "accurate": False, "latency": 0})

async def run_tiered_test(target_model: str, load_test_config):
    semaphore = asyncio.Semaphore(load_test_config["concurrent_clients"])
    results = []
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Warmup
        await client.post("http://test/route", json={"model": target_model, "prompt": "warmup"}, timeout=120.0)
        
        start_time = time.time()
        tasks = [send_request(client, semaphore, results, target_model) for _ in range(load_test_config["total_requests"])]
        await asyncio.gather(*tasks)
        end_time = time.time()
        
    return results, start_time, end_time

def test_tiered_optimization_impact(load_test_config):
    """
    Tests how the Ember Fast-Tier improves RPS and Latency for a heavy model (mistral).
    """
    target_model = "mistral" # This would normally be slow
    total_requests = load_test_config["total_requests"]
    
    print(f"\nStarting TIERED OPTIMIZATION load test for '{target_model}' (Fast-Tier: Ember)...")
    
    results, start_time, end_time = asyncio.run(run_tiered_test(target_model, load_test_config))
    
    duration = end_time - start_time
    successful = [r for r in results if r["success"]]
    accurate = [r for r in results if r["accurate"]]
    latencies = [r["latency"] for r in successful]
    
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    accuracy_pct = (len(accurate) / len(successful) * 100) if successful else 0
    
    print(f"\n==========================================")
    print(f"Tiered Routing Results ({target_model} with Ember Fast-Tier):")
    print(f"==========================================")
    print(f"Total Requests: {total_requests}")
    print(f"Avg Latency: {avg_latency:.4f}s")
    print(f"Accuracy Rate: {accuracy_pct:.2f}%")
    print(f"Total Duration: {duration:.2f}s")
    print(f"Throughput (RPS): {total_requests / duration:.2f}")
    print(f"==========================================")
    
    # We expect RPS to be significantly higher than pure Mistral (which is ~1-2 RPS on CPU)
    # If Ember is catching a good chunk, we should see a much higher overall RPS.
