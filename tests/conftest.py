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
from common.otel import flush_otel, init_otel, get_tracer
from concurrent.futures import ThreadPoolExecutor

@pytest.fixture(scope="session", autouse=True)
def setup_otel():
    """
    Initialize OTel at the start of the test session and flush it at the end.
    """
    init_otel()
    yield
    flush_otel()

@pytest.fixture(scope="session")
def shared_executor():
    """
    Provides a shared ThreadPoolExecutor for testing, ensuring it's shut down 
    at the end of the test session. The pool size is driven by configuration.
    """
    from common.config import Config
    config = Config()
    app_config = getattr(config.baseConfig, "application", None)
    max_workers = getattr(app_config, "threadPoolSize", 100)
    
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
