# Origami AI Router - Common Package (`origami-common`)

The `origami-common` package provides enterprise observability abstractions, OpenTelemetry integrations, and shared utility helpers across the Origami AI Router monorepo.

---

## Key Features & Modules

- **`origami_common.otel`**:
  - `init_otel(config)`: Initializes global OpenTelemetry `TracerProvider` and `LoggerProvider` instances.
  - `get_tracer(name)`: Returns a named tracer attached to Google Cloud Trace (`CloudTraceSpanExporter`) or standard OTel exporters.
  - `flush_otel()`: Forces a sync flush of all active span queues before service shutdown.
- **`origami_common.utils`**:
  - General helper utilities, dictionary transformations, and text parsing routines.

---

## Installation

```bash
uv sync --package origami-common
```

---

## Usage Example

```python
from origami_api.config import Config
from origami_common.otel import init_otel, get_tracer, flush_otel

# 1. Load application configuration
config = Config()

# 2. Bootstrap OpenTelemetry global providers
init_otel(config)

# 3. Create a tracer for custom telemetry spans
tracer = get_tracer("my_service")

with tracer.start_as_current_span("custom_routing_span") as span:
    span.set_attribute("router.environment", "production")
    # Perform operational work...

# 4. Flush telemetry on shutdown
flush_otel()
```

---

## Dependencies

- `opentelemetry-api` & `opentelemetry-sdk`
- `opentelemetry-exporter-gcp-trace` & `opentelemetry-exporter-gcp-logging`
