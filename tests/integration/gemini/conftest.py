import time
import pytest
import threading
import uvicorn
import httpx
from typing import Dict, Any

from edgerouter_api.config import Config
from edgerouter.main import app
from tests.integration.data import get_test_env_setting
from common.otel import flush_otel

@pytest.fixture(scope="session")
def app_config(session_config):
    """Provides the EdgeRouter Config object."""
    return session_config

@pytest.fixture(scope="session")
def load_test_config() -> Dict[str, Any]:
    """Returns the configuration map for the Gemini load test."""
    host = "127.0.0.1"
    port = int(get_test_env_setting("server_port_gemini", "8006"))
    return {
        "server_host": host,
        "server_port": port,
        "base_url": f"http://{host}:{port}",
        "total_requests": int(get_test_env_setting("total_requests", "100")),
        "concurrent_clients": int(get_test_env_setting("concurrent_clients", "10"))
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
