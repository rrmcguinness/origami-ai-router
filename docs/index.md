# Origami AI Router

**Origami AI Router** is an enterprise-grade LLM routing and inference service designed for extreme scalability, operational security, observability, and sub-second latency. It acts as a stateless traffic controller at the edge of multi-agent cognitive architectures, sitting in front of stateful orchestrators (such as Google Agent Development Kit) and routing requests dynamically to cloud or edge models while protecting agent contexts from prompt vector attack poisoning.

---

## Key Features

- **Multi-Backend Architecture**: Seamlessly route queries between Google Gemini (Cloud), vLLM (GPU Batching), llama.cpp (Edge CPU/GPU), and Ember (Embedding Interception).
- **Operational Security Pre-Filter (`origami_ops_sec`)**: Real-time vector attack classification (`< 50ms`) protecting against prompt injection, system prompt exfiltration, jailbreak roleplay, command injection, and data exfiltration before payloads reach downstream models.
- **Ember Fast-Tier Interception**: Sub-20ms intent classification powered by `BAAI/bge-m3` cosine similarity, bypassing heavy LLM execution for high-frequency queries.
- **Enterprise Observability**: Native OpenTelemetry (OTel) integration with standardized span attributes for Google Cloud Trace & Logging.
- **Zero-Fat Chain of Thought (CoT)**: Cryptic shorthand reasoning boundaries capping latency jitter while isolating deep reflection to cloud endpoints.
- **Stateless & Modular**: Distributed as a clean `uv` monorepo containing decoupled python packages (`origami-common`, `origami-stateless`, `origami-gemini`, `origami-vllm`, `origami-llama-cpp`, `origami-ember`, `origami-ops-sec`, `origami-api`).

---

## Quick Navigation

<div class="grid cards" markdown>

-   :material-sitemap: **[Architecture Overview](architecture/index.md)**
    
    Deep dive into the 11-agent execution matrix, cloud-to-edge topology, and stateless session design.

-   :material-shield-check: **[Operational Security (OpsSec)](architecture/ops-sec.md)**
    
    Explore `before_route` threat protection, store-and-slim context intermediary sanitization, and multi-vector rules.

-   :material-lightning-bolt: **[ADK Best Practices](architecture/adk-best-practices.md)**
    
    Learn how `before_agent_callback` pre-routing slashes delivery latency by 50% over dynamic tool-calling.

-   :material-tune: **[Setup & CUDA Configuration](setup/cuda.md)**
    
    Instructions for hardware acceleration, `llama-cpp-python` CUDA compilation, and performance tuning.

-   :material-chart-bar: **[Performance & Benchmarks](evaluations/performance-report.md)**
    
    Throughput RPS metrics, cost scaling projections, and multi-model benchmark comparisons.

-   :material-shield-sync: **[OpsSec Evaluation Report](evaluations/ops-sec-evaluation.md)**
    
    Review 0.80ms cached index initialization, sub-50ms vector query benchmarks, and rule evaluation metrics.

</div>

---

## Quick Start

```bash
# 1. Sync workspace dependencies via uv
uv sync --all-packages --group docs

# 2. Provision local GGUF weights & embedding models (~20GB)
chmod +x ./models/fetch-models.sh
./models/fetch-models.sh

# 3. Launch the Origami AI Router service with OpsSec enabled
uv run origami-router --enable-ops-sec
```

For full setup guidelines, consult the [Architecture Documentation](architecture/index.md).
