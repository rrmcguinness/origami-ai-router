# EdgeRouter

EdgeRouter is an enterprise-grade LLM routing and inference service designed for scalability, observability, and flexibility. It supports multiple backends including Google Gemini, vLLM, and llama.cpp, allowing for optimized model delivery across various environments.

## Features

- **Multi-Backend Support**: Seamlessly route requests to Gemini, vllm, or llama.cpp.
- **Enterprise Observability**: Integrated with OpenTelemetry for tracing and logging (GCP Cloud Trace & Logging).
- **Stateless Routing**: Clean abstractions for building stateless LLM routers.
- **Retail-Optimized**: Designed for performance in high-demand environments.

## Project Structure

This project is managed as a `uv` workspace:

- `src/edgerouter`: The main FastAPI application and entry point.
- `packages/common`: Shared utilities, configuration (TOML), and telemetry.
- `packages/stateless_router`: Base abstractions and Pydantic models for routers.
- `packages/gemini_router`: Google Gemini model implementation.
- `packages/vllm_router`: high-performance inference using vLLM (Linux/CUDA).
- `packages/llama_cpp_router`: Local model execution via llama.cpp.

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
uv run edgerouter
```

## Documentation

For detailed information on specific topics, refer to the following documents:

- [Architecture Overview](docs/ARCH_OVERVIEW.md) - Deep dive into the system design.
- [ADK Usage Guide](docs/ADK_USAGE.md) - How to use the Agent Development Kit.
- [Accuracy Report](docs/ACCURACY_REPORT.md) - Performance and model accuracy metrics.
- [CUDA Setup](docs/CUDA_SETUP.md) - Instructions for GPU acceleration.

## Development

### Running Tests

```bash
uv run pytest
```

---
*Created with love (and a bit of sarcasm) by Ariana.*
