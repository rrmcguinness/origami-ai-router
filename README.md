# OrigamiRouter

OrigamiRouter is an enterprise-grade LLM routing and inference service designed for scalability, observability, and flexibility. It supports multiple backends including Google Gemini, vLLM, and llama.cpp, allowing for optimized model delivery across various environments.

## Features

- **Multi-Backend Support**: Seamlessly route requests to Gemini, vllm, or llama.cpp.
- **Enterprise Observability**: Integrated with OpenTelemetry for tracing and logging (GCP Cloud Trace & Logging).
- **Stateless Routing**: Clean abstractions for building stateless LLM routers.
- **Retail-Optimized**: Designed for performance in high-demand environments.

## Project Structure

This project is managed as a `uv` workspace:

- `src/origami-router`: The main FastAPI application and entry point.
- `packages/origami_common`: Shared utilities, configuration (TOML), and telemetry.
- `packages/origami_stateless`: Base abstractions and Pydantic models for routers.
- `packages/origami_gemini`: Google Gemini model implementation.
- `packages/origami_vllm`: high-performance inference using vLLM (Linux/CUDA).
- `packages/origami_llama_cpp`: Local model execution via llama.cpp.

## Getting Started

### Prerequisites

- Python 3.13 (managed via `uv`)
- `uv` package manager

### Installation

```bash
uv sync --all-packages
```

### Running the Service

```bash
uv run origami-router
```

## Documentation

For detailed information on specific topics, refer to the following documents:

- [Architecture Overview](docs/architecture-overview.md) - Deep dive into the system design.
- [ADK Usage Guide](docs/google-adk-best-practices.md) - How to use the Agent Development Kit.
- [Performance & Accuracy Report](docs/router_performance_report.md) - Performance and model accuracy metrics.
- [CUDA Setup](docs/nvidia-cuda-setup.md) - Instructions for GPU acceleration.

## Development

### Running Tests

The test suite is segmented into specific categories using `pytest` markers for precise execution:

```bash
# Run everything
uv run pytest

# Run only unit tests
uv run pytest -m "unit"

# Run only integration tests
uv run pytest -m "integration"

# Run load tests
uv run pytest -m "load"

# Run regression tests
uv run pytest -m "regression"
```

You can combine markers if needed (e.g., `uv run pytest -m "unit or integration"`).

---
*Created with love (and a bit of sarcasm) by Ariana.*
