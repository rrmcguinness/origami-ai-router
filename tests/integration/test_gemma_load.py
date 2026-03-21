import pytest
import time
import random
import threading
import uvicorn
import httpx
import asyncio
from edgerouter.main import app
from .data import RETAIL_TEST_CASES
from common.otel import get_tracer, flush_otel

# Configuration for the load test
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8005  # Use a different port to avoid conflicts
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
TOTAL_REQUESTS = 1000
CONCURRENT_CLIENTS = 10 

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
        pytest.fail("Server failed to start in time for load test.")
    
    yield
    flush_otel()

async def send_request(client, semaphore, results, tracer):
    """Sends a single routing request with a random test case."""
    async with semaphore:
        with tracer.start_as_current_span("load_test.send_request") as span:
            prompt, expected = random.choice(RETAIL_TEST_CASES)
            payload = {
                "model": "gemma",
                "prompt": prompt
            }
            span.set_attribute("test.prompt", prompt)
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
    
    with tracer.start_as_current_span("load_test.execution_loop"):
        async with httpx.AsyncClient() as client:
            tasks = [send_request(client, semaphore, results, tracer) for _ in range(TOTAL_REQUESTS)]
            await asyncio.gather(*tasks)
    
    return results

def test_gemma_load():
    """
    Executes a load test of 1000 requests against the Gemma router.
    Uses asyncio to ensure concurrent execution from the client side.
    Instrumented with OTel spans for trace analysis.
    """
    tracer = get_tracer("gemma_load_test")
    
    with tracer.start_as_current_span("gemma_load_test.total_execution") as parent_span:
        print(f"\nStarting INSTRUMENTED ASYNC load test: {TOTAL_REQUESTS} requests...")
        
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
        
        print(f"\nAsync Load Test Results:")
        print(f"Total Requests: {TOTAL_REQUESTS}")
        print(f"Successful: {success_count}")
        print(f"Failed: {failure_count}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Requests Per Second: {TOTAL_REQUESTS / duration:.2f}")

        assert success_count == TOTAL_REQUESTS
