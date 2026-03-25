# OrigamiRouter - Common Package

The `common` package provides shared utilities, configuration management, and observability foundations for the OrigamiRouter project.

## Key Modules

- **`config.py`**: Handles TOML configuration file parsing and validation.
- **`model.py`**: Shared data models used across the application.
- **`otel.py`**: OpenTelemetry integration for tracing and logging to Google Cloud Trace and Cloud Logging.
- **`api.py`**: Shared API utilities and client abstractions.
- **`utils.py`**: General purpose utility functions.

## Usage

This package is a core dependency for all routers and the main application. It is expected to be used as a local workspace dependency.

```python
from common import config, otel
```

## Dependencies

- `toml`: For configuration parsing.
- `google-cloud-aiplatform`: Vertex AI integration components.
- `opentelemetry-api`, `opentelemetry-sdk`: Observability framework.
- `opentelemetry-exporter-gcp-trace/logging`: Exporting telemetry to GCP.
