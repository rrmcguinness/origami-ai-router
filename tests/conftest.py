import pytest
import os
from common.otel import flush_otel, init_otel, get_tracer

@pytest.fixture(scope="session", autouse=True)
def setup_otel():
    """
    Initialize OTel at the start of the test session and flush it at the end.
    """
    init_otel()
    yield
    flush_otel()

@pytest.fixture(scope="function", autouse=True)
def test_span(request):
    """
    Wraps each test in an OTel span.
    """
    tracer = get_tracer("tests")
    with tracer.start_as_current_span(request.node.name) as span:
        yield span
