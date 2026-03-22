import pytest
import time
import random
import httpx
import asyncio
from edgerouter.main import app
from .data import RETAIL_TEST_CASES
from common.otel import get_tracer, flush_otel
from common.config import Config

from opentelemetry.propagate import inject

TOTAL_REQUESTS = 2000
CONCURRENT_CLIENTS = 250 

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
            span.set_attribute("test.prompt", prompt)
            
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
        print(f"Warming up Local AI Router for model '{target_model}'...")
        await client.post("http://test/route", json={"model": target_model, "prompt": "warmup"}, timeout=120.0)
        print("Warmup complete. Starting load generation.")
        
        start_time = time.time()
        with tracer.start_as_current_span("load_test.execution_loop"):
            tasks = [send_request(client, semaphore, results, tracer, target_model) for _ in range(TOTAL_REQUESTS)]
            await asyncio.gather(*tasks)
        end_time = time.time()
        
    return results, start_time, end_time

def test_gemma_load():
    """
    Executes a load test of 1000 requests against the Gemma router.
    Uses asyncio to ensure concurrent execution from the client side.
    Instrumented with OTel spans for trace analysis.
    """
    tracer = get_tracer("local_router_load_test")
    
    with tracer.start_as_current_span("local_router_load_test.total_execution") as parent_span:
        cfg = Config()
        test_cfg = getattr(cfg.baseConfig, "test", None)
        target_model = getattr(test_cfg, "model", "gemma")
        
        print(f"\nStarting INSTRUMENTED ASYNC load test for model '{target_model}': {TOTAL_REQUESTS} requests...")
        
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

        assert success_count == TOTAL_REQUESTS
