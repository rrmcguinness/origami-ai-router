# Origami AI Router

**Origami AI Router** is an enterprise-grade LLM routing and inference service designed for extreme scalability, observability, and sub-second latency. It acts as a stateless traffic controller at the edge of multi-agent cognitive architectures, sitting in front of stateful orchestrators (such as Google Agent Development Kit) and routing requests dynamically to cloud or edge models.

---

## Key Features

- **Multi-Backend Architecture**: Seamlessly route queries between Google Gemini (Cloud), vLLM (GPU Batching), llama.cpp (Edge CPU/GPU), and Ember (Embedding Interception).
- **Ember Fast-Tier Interception**: Sub-20ms intent classification powered by `BAAI/bge-m3` cosine similarity, bypassing heavy LLM execution for high-frequency queries.
- **Enterprise Observability**: Native OpenTelemetry (OTel) integration with standardized span attributes for Google Cloud Trace & Logging.
- **Zero-Fat Chain of Thought (CoT)**: Cryptic shorthand reasoning boundaries capping latency jitter while isolating deep reflection to cloud endpoints.
- **Stateless & Modular**: Distributed as a clean `uv` monorepo containing decoupled python packages (`origami-common`, `origami-stateless`, `origami-gemini`, `origami-vllm`, `origami-llama-cpp`, `origami-ember`, `origami-api`).

---

## Quick Navigation

<div class="grid cards" markdown>

-   :material-sitemap: **[Architecture Overview](architecture/index.md)**
    
    Deep dive into the 11-agent execution matrix, cloud-to-edge topology, and stateless session design.

-   :material-lightning-bolt: **[ADK Best Practices](architecture/adk-best-practices.md)**
    
    Learn how `before_agent_callback` pre-routing slashes delivery latency by 50% over dynamic tool-calling.

-   :material-tune: **[Setup & CUDA Configuration](setup/cuda.md)**
    
    Instructions for hardware acceleration, `llama-cpp-python` CUDA compilation, and performance tuning.

-   :material-chart-bar: **[Performance & Benchmarks](evaluations/performance-report.md)**
    
    Throughput RPS metrics, cost scaling projections, and multi-model benchmark comparisons.

</div>

---

## Quick Start

```bash
# 1. Sync workspace dependencies via uv
uv sync --all-packages --group docs

# 2. Provision local GGUF weights & embedding models (~20GB)
chmod +x ./models/fetch-models.sh
./models/fetch-models.sh

# 3. Launch the Origami AI Router service
uv run origami-router
```

For full setup guidelines, consult the [Architecture Documentation](architecture/index.md).
