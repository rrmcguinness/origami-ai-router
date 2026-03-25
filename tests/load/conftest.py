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

import os
import time
import pytest
import threading
import uvicorn
import httpx
from typing import Dict, Any

# Ensure tests within this directory strictly load `.env.load.toml`
os.environ["RUNTIME_ENV"] = "load"

from origami_api.config import Config
from origami_router.main import app
from origami_common.otel import flush_otel

@pytest.fixture(scope="session")
def app_config(session_config):
    """Provides the EdgeRouter Config object."""
    return session_config

@pytest.fixture(scope="session")
def load_test_config(session_config: Config) -> Dict[str, Any]:
    """Returns the configuration map for the Gemini load test."""
    host = session_config.server.host
    port = session_config.server.port
    total_requests = session_config.load_test.total_requests
    concurrent_clients = session_config.load_test.concurrent_clients

    return {
        "server_host": host,
        "server_port": port,
        "base_url": f"http://{host}:{port}",
        "total_requests": total_requests,
        "concurrent_clients": concurrent_clients
    }


def _run_server(host: str, port: int):
    """Starts the FastAPI server in a separate thread."""
    uvicorn.run(app, host=host, port=port, log_level="error")

@pytest.fixture(scope="session", autouse=True)
def engine_service(load_test_config):
    """Fixture to start and stop the server for the duration of the test session."""
    server_thread = threading.Thread(
        target=_run_server,
        args=(load_test_config["server_host"], load_test_config["server_port"]),
        daemon=True
    )
    server_thread.start()
    
    # Wait for the server to be ready
    base_url = load_test_config["base_url"]
    timeout = 15
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with httpx.Client() as client:
                response = client.get(f"{base_url}/health")
                if response.status_code == 200:
                    break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        pytest.fail("Server failed to start in time for Gemini tests.")
    
    yield
    flush_otel()
