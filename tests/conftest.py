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
from origami_common.otel import flush_otel, init_otel, get_tracer
from concurrent.futures import ThreadPoolExecutor

@pytest.fixture(scope="session")
def session_config():
    """Provides a singleton Config instance for the test session."""
    import os
    # Ensure integration or default test environment is prioritized over local
    if "RUNTIME_ENV" not in os.environ:
        os.environ["RUNTIME_ENV"] = "integration"
        
    from origami_api.config import Config
    import origami_router.state as edgestate
    if edgestate.config is None:
        edgestate.config = Config()
    return edgestate.config

@pytest.fixture(scope="session", autouse=True)
def setup_otel(session_config):
    """
    Initialize OTel at the start of the test session and flush it at the end.
    """
    init_otel(session_config)
    yield
    flush_otel()

@pytest.fixture(scope="session")
def shared_executor(session_config):
    """
    Provides a shared ThreadPoolExecutor for testing, ensuring it's shut down 
    at the end of the test session. The pool size is driven by configuration.
    """
    max_workers = session_config.application.threadPoolSize or 100
    
    executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="test-executor")
    yield executor
    executor.shutdown(wait=True)

@pytest.fixture(scope="function", autouse=True)
def test_span(request):
    """
    Wraps each test in an OTel span.
    """
    tracer = get_tracer("tests")
    with tracer.start_as_current_span(request.node.name) as span:
        yield span

@pytest.fixture(scope="session", autouse=True)
def cleanup_routers():
    """Ensure routers are cleared and deleted before interpreter shutdown to prevent llama-cpp-python GC crashes."""
    yield
    import origami_router.state as edgestate
    if hasattr(edgestate, "active_routers"):
        edgestate.active_routers.clear()
    import gc
    gc.collect()
