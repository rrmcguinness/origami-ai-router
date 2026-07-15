# Origami AI Router

Origami AI Router is an enterprise-grade LLM routing and inference service designed for scalability, operational security, observability, and flexibility. It supports multiple backends including Google Gemini, vLLM, llama.cpp, and Ember embeddings, allowing for optimized model delivery across various environments while protecting multi-agent conversation contexts from prompt vector attack poisoning.

## Features

- **Multi-Backend Support**: Seamlessly route requests to Gemini, vLLM, llama.cpp, or Ember.
- **Operational Security Pre-Filter (`origami_ops_sec`)**: Sub-50ms vector attack classification protecting against prompt injection, system prompt exfiltration, jailbreak roleplay, command code injection, and data exfiltration.
- **Fast-Tier Interception (`EmberRouter`)**: Sub-20ms intent classification using `BAAI/bge-m3` cosine similarity.
- **Enterprise Observability**: Integrated with OpenTelemetry for tracing and logging (GCP Cloud Trace & Logging).
- **Stateless Routing**: Clean abstractions for building stateless LLM routers with zero-downtime hot-swapping (`POST /admin/rules/reload`).
- **Retail-Optimized**: Designed for performance in high-demand enterprise environments.

## Project Structure

This project is managed as a `uv` workspace:

- `src/origami-router`: The main FastAPI application, decoupled routing pipeline, and service entry point.
- `packages/origami_common`: Shared utilities, configuration (TOML), and telemetry.
- `packages/origami_stateless`: Base abstractions and Pydantic models for routers and builder factories.
- `packages/origami_ops_sec`: Operational security analyzer, vector attack definitions, and ADK before_model_callback hooks.
- `packages/origami_gemini`: Google Gemini model implementation.
- `packages/origami_vllm`: High-performance inference using vLLM (Linux/CUDA).
- `packages/origami_llama_cpp`: Local model execution via llama.cpp.
- `packages/origami_ember`: Ultra-fast "Fast-Tier" routing using BGE-M3 text embeddings for sub-20ms interception.

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

> **Note:** The `fetch-models.sh` script leverages `huggingface-cli` to download the `bge-m3` embedding model directly into your local `models/bge-m3/` directory, while fetching specific Q4_K_M quantized weights for the fallback LLMs (Llama 3.1, Gemma 3, and Mistral NeMo).

### Configuration

Origami AI Router uses a hierarchical configuration system defined in `.env.toml`. Operational security rules are defined in `rules_ops_sec.toml` and routing rules in `rules_router.toml`. To provide local overrides (such as API keys), create a `.env.local.toml` file in the project root:

```toml
[application]
enable_ops_sec = true
rules_routing = "rules_router.toml"
rules_ops_sec = "rules_ops_sec.toml"

[ai_models.router]
api_key = "YOUR_GOOGLE_AI_STUDIO_API_KEY"

[ai_models.embeddings]
api_key = "YOUR_GOOGLE_AI_STUDIO_API_KEY"
```

### Running the Service

```bash
# Launch service with OpsSec protection enabled
uv run origami-router --enable-ops-sec
```

## Advanced Architectures

### 1. Operational Security Pre-Routing & Safe Context Intermediary
Origami AI Router includes a dedicated pre-routing operational security layer (`origami_ops_sec`). When a request enters the pipeline, `OpsSecPreFilterStep` evaluates the input against 260+ vector attack examples using `BAAI/bge-m3` embeddings in **< 50ms**.

If a threat is detected:
- **`slim` mode**: The raw attack is safely saved to session telemetry state, while the user content in the prompt sent to the LLM turn is replaced with a neutralized tag (`"[NEUTRALIZED PROMPT VECTOR ATTACK: ..."]`), preventing context poisoning.
- **`block` mode**: Execution is halted immediately and a fallback security alert is returned.

### 2. Tiered Routing Optimization (Fast-Tier)
Origami AI Router implements a multi-stage routing pipeline to dramatically increase Throughput (RPS) and lower average latency. When a heavy reasoning model (like Gemini or Mistral) is requested, the prompt is evaluated by `EmberRouter`—a local, CPU-efficient embedding model (`BAAI/bge-m3`).

If the user's intent matches a known agent definition with a high confidence score (`confidence_threshold`), the router intercepts the request and responds in milliseconds, completely bypassing heavy LLM execution. 

### 3. Zero-Fat Chain of Thought Routing
Origami AI Router utilizes an advanced hybrid routing technique to achieve high-accuracy heuristic reasoning at the Cloud layer, while mathematically stripping out the latency cost typically associated with LLM Chain-of-Thought (CoT).

**Methodology for Minimizing Time-To-First-Route (TTFR):**
1. **Delegative API Over Orchestration Hooks:** Rely natively on the lower-level API Router (`get_routing_decision`), stripping out multi-turn execution latency.
2. **Ultra-Brief CoT Prompting:** Inside `GeminiRouter`, instructions enforce extremely dense, cryptic shorthand evaluations (e.g., `{"reasoning": "kwd:brakes->auto->dumpster_fire_handler"}`), slashing generation overhead from ~40+ tokens to ~5 tokens cleanly.
3. **Hard Mechanical Ceilings:** Strictly limits `max_output_tokens: 100` to forcefully cap generation loops and mitigate latency jitter.

## Customizing the Router & Security Rules

Building custom routes or attack vectors is managed via standard TOML configurations:

- **Routing Rules**: `rules_router.toml` (or `rules.toml`) defines target agents and example prompts.
- **OpsSec Rules**: `rules_ops_sec.toml` defines vector attack categories, severities, actions (`slim`, `block`), and training examples.
- **Zero-Downtime Hot-Reloading**: Trigger `POST /admin/rules/reload` to atomically reload rules in production without restarting the service.

## Documentation

For detailed information on specific topics, refer to our [Documentation Site](docs/index.md) or specific guides:

- [Architecture Overview](docs/architecture/index.md) - Deep dive into system design and multi-tier routing.
- [Operational Security Architecture](docs/architecture/ops-sec.md) - Pre-route firewall, context intermediary mechanics, and rules.
- [OpsSec Vector Performance Report](docs/evaluations/ops-sec-evaluation.md) - 0.80ms cached index benchmarks and latency breakdown.
- [ADK Best Practices](docs/architecture/adk-best-practices.md) - How to leverage pre-routing callbacks in Agent Development Kit.
- [Performance & Accuracy Report](docs/evaluations/performance-report.md) - Throughput, RPS scaling, and benchmark metrics.
- [CUDA Setup Guide](docs/setup/cuda.md) - Instructions for GPU compilation and hardware acceleration.

## Development

### Running Tests

The test suite is segmented into specific categories using `pytest` markers for precise execution:

```bash
# Run full suite including OpsSec tests
uv run pytest

# Run OpsSec unit & integration tests
uv run pytest packages/origami_ops_sec/tests/ tests/integration/ops_sec/

# Run only unit tests
uv run pytest -m "unit"

# Run regression tests
uv run pytest -m "regression"
```

---
*Created with love (and a bit of sarcasm) by Ariana.*
