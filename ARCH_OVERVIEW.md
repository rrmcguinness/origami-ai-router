# EdgeRouter Architectural Overview

## Executive Summary

The **EdgeRouter** is a high-performance, stateless routing layer designed to sit at the "edge" of an AI agentic system. Its primary purpose is to decompose complex user prompts into specialized execution routes with sub-100ms latency. By decoupling routing logic from the stateful conversation orchestrator, the system achieves massive horizontal scalability while maintaining strict structural integrity.

## Core Advantages

### 1. High Throughput (TPS) Scaling

- **Stateless Execution**: Traditional "Sub-Agent" routers often process the entire conversation history to determine the next step. This increases token volume and compute time exponentially as conversations grow.
- **Isolated Intent**: EdgeRouter focuses on the _latest_ intent. This allows the use of hyper-optimized kernels like **vLLM (PagedAttention)** which can batch 200+ concurrent routing requests on a single GPU—achieving throughput that is orders of magnitude higher than a sequential stateful agent.

### 2. Cache Hit Optimization

- **Static System Context**: Because the router uses a fixed set of `RoutingRules` and a structured system prompt, the **KV-Cache** on the serving engine (Gemini or vLLM) remains almost entirely "hot."
- **Zero-Shot Focus**: By avoiding the injection of variable conversation history into the routing prompt, we ensure the prefix remains identical across millions of requests, allowing the hardware to skip repetitive prompt processing.

### 3. Latency Reduction

- **Model Specialization**: High-speed routing uses "Distilled" or "Small" models (e.g., Gemma 3 or Gemini Flash) which have significantly lower inference times than "Reasoning" models used for stateful execution.
- **Structural Forcing (GBNF)**: By using Llama.cpp grammars, we ensure the output is _always_ valid JSON. This eliminates the "validation-loop" latency common in standard agents that might produce malformed choices.

### 4. Advanced Guardrails

- **Immediate Pre-Filtering**: The EdgeRouter acts as a "Bouncer." It can identify toxic content, off-topic requests, or "prompt injections" before those tokens are ever processed by a more expensive (and potentially vulnerable) stateful orchestrator.
- **Safety Isolation**: Routing a request to a `Fallback` or `Blocked` agent happens at the edge, protecting the internal conversation state from contamination by malicious input.

---

## Pros and Cons

| Feature         | Pros                                    | Cons                                                        |
| :-------------- | :-------------------------------------- | :---------------------------------------------------------- |
| **Performance** | Extremely low latency and high TPS.     | Requires dedicated serving infrastructure for local models. |
| **Cost**        | Uses cheaper tokens (Small models).     | Provisioned throughput reservations carry fixed costs.      |
| **Reliability** | Deterministic JSON output via Grammars. | May misinterpret vague references without history.          |
| **Logic**       | Clean separation of concerns.           | Adds one additional hop in the network architecture.        |

---

## Critical Analysis & Blindspots

To ensure a non-biased representation, the following trade-offs across our different implementations must be acknowledged:

### 1. General Architectural Trade-offs

#### The "Context Blindness" Trap

Because this router is **Stateless**, it has no memory of the last three turns. If a user asks a follow-up like _"Tell me more about that second one,"_ a stateless router may lack the context to know what "that" refers to.

- **Mitigation**: The Orchestrator must pass an "Intent Summary" or "Reference Context" into the EdgeRouter prompt to resolve pronouns, which slightly increases the token count but preserves the stateless engine architecture.

#### Model "Intelligence" Ceiling

Using a 270M or 2B model for routing is fast, but it lacks the nuanced reasoning of a 1.7T model. It may struggle with "Sarcasm" or "Indirect Intent" that a stateful reasoning agent would catch via reflection.

---

### 2. Implementation-Specific Blindspots

#### Managed Cloud (Gemini Flash)

- **The "Network Jitter" Tax**: Unlike local routers, Gemini's latency is subject to the public internet or VPC-to-Backbone overhead. A sub-100ms routing decision can be delayed to 500ms+ by a single network hiccup, negating the "Edge" benefit.
- **API Quota Cascades**: Standard tiers are subject to RPM (Requests Per Minute) limits. Without **Provisioned Throughput**, a sudden burst in traffic can return `429 Too Many Requests`, effectively "blinding" the entire orchestrator until the window resets.

#### Local GPU (vLLM Engine)

- **VRAM Greed**: vLLM is designed for maximum throughput and pre-allocates significant VRAM for its KV-cache. Running the router on the same GPU as a secondary service is a high-risk OOM (Out of Memory) scenario without strict `gpu_memory_utilization` caps.
- **Hardware Lock-in**: This implementation is strictly NVIDIA/Linux-dependent. It offers the highest performance but zero portability for non-datacenter environments.

#### Local Edge/CPU (Llama.cpp)

- **The Scaling Wall**: Unlike vLLM, Llama.cpp does not support native continuous batching for routing. Scaling to 100+ RPS requires a "Worker Pool" strategy where each worker is a separate isolated instance. This consumes memory and CPU linearly, creating a hard "scaling ceiling" based on physical core counts.
- **Thermal Throttling Inconsistency**: On local Apple Silicon or Edge hardware, sustained high-load routing can trigger thermal management. This leads to "performance drift" where the first 1,000 requests are sub-100ms, but subsequent requests slow down as the SOC throttles.

#### Grammar Rigidity (Llama.cpp specific)

- **GBNF Brittle-ness**: GBNF grammars are powerful but strictly deterministic. If the routing agents list changes dynamically in the DB, the grammar must be recompiled or updated on the fly. A failure in grammar generation will cause the worker to crash or hang.
