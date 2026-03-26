# Origami AI Router

Origami AI Router is an enterprise-grade LLM routing and inference service designed for scalability, observability, and flexibility. It supports multiple backends including Google Gemini, vLLM, and llama.cpp, allowing for optimized model delivery across various environments.

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
- `packages/origami_ember`: Ultra-fast "Fast-Tier" routing using BGE-M3 text embeddings for sub-10ms interception.

## Getting Started

### Prerequisites

- Python 3.13 (managed via `uv`)
- `uv` package manager

### Installation & Model Provisioning

Origami AI Router dynamically leverages local models for off-cloud Edge inference and Fast-Tier routing. To ensure you have the required `.gguf` weights and `BAAI/bge-m3` embedding tensors downloaded, run the setup commands below:

```bash
# 1. Sync the workspace dependencies
uv sync --all-packages

# 2. Provision the required local models (~20GB total download)
chmod +x ./models/fetch-models.sh
./models/fetch-models.sh
```

> **Note:** The `fetch-models.sh` script leverages the `huggingface-cli` to download the `bge-m3` embedding model directly into your local `models/bge-m3/` directory, while fetching specific Q4_K_M quantized weights for the fallback LLMs (Llama 3.1, Gemma 3, and Mistral NeMo).

### Running the Service

```bash
uv run origami-router
```

## Advanced Architectures

### 1. Tiered Routing Optimization (Fast-Tier)
Origami AI Router implements a multi-stage routing pipeline to dramatically increase Throughput (RPS) and lower average latency. When a heavy reasoning model (like Gemini or Mistral) is requested, the prompt is first evaluated by the `EmberRouter`—a local, CPU-efficient embedding model (`BAAI/bge-m3`). 

If the user's intent matches a known agent definition with a high confidence score (configurable via `confidence_threshold`), the router intercepts the request and responds in milliseconds, completely bypassing the heavy LLM execution. 

### 2. Zero-Fat Chain of Thought Routing
Origami AI Router utilizes an advanced hybrid routing technique to achieve high-accuracy heuristic reasoning at the Cloud layer, while mathematically stripping out the latency cost typically associated with LLM Chain-of-Thought (CoT).

**Methodology for Minimizing Time-To-First-Route (TTFR):**
1. **Delegative API Over Orchestration Hooks:** Do not force high-level ADK agents to generate lengthy XML `<thinking>` blocks simply to determine routing. Instead, rely natively on the lower-level API Router (`get_routing_decision`), stripping out multi-turn execution latency.
2. **Ultra-Brief CoT Prompting:** Inside the `GeminiRouter`, the instruction enforces extremely dense, cryptic shorthand evaluation (e.g., `{"reasoning": "kwd:brakes->auto->dumpster_fire_handler"}`). This slashes generation overhead from ~40+ tokens to ~5 tokens cleanly.
3. **Hard Mechanical Ceilings:** The `GeminiRouter` configuration strictly limits `max_output_tokens: 100`, which forcefully caps generation loops and physically mitigates latency jitter, preventing runaway LLM cycles.

By embedding these boundaries, Cloud orchestrators retain extreme logical precision at a fraction of the TTFR cost, while Edge fallback node performance (e.g., Llama/vLLM) remains perfectly unburdened by CoT generation loops.

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
