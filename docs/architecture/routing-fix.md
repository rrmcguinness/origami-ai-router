# Solving Multi-Agent Latency Bottlenecks with Origami AI Router

In multi-agent systems, sequential agent delegation is a hidden killer of enterprise performance. Relying on a "Coordinator" agent to think, call a tool, and then pass a request to a "Specialist" introduces a massive **latency tax.**

**Origami AI Router** solves this by decoupling intent decomposition from stateful orchestration, resulting in a **68% reduction in total delivery latency.**

---

## 1. The Sub-Agent Overhead Problem

Traditional agents process entire conversation histories just to decide what to do next. As chats grow, token volume and compute time scale exponentially.

**Origami AI Router is 100% stateless.** It focuses strictly on the immediate intent and minimal context summary, keeping KV-caches hot and compute times sub-100ms.

---

## 2. Multi-Backend Flexibility: Cloud & Edge

- **Google Gemini 3.5 Flash**: Cloud gold standard for complex reasoning with **~96%+ accuracy.**
- **Ember Fast-Tier (BGE-M3 Embeddings)**: Ultra-fast local sub-10ms routing interceptor running at ~48 RPS on CPU, evaluating cosine similarity to bypass LLM latency completely.
- **vLLM (Local GPU)**: High throughput (500+ RPS) leveraging continuous PagedAttention batching.
- **Llama.cpp (Local Edge/CPU)**: GBNF Grammars for structural forcing, ensuring valid JSON formatting on every turn.

---

## 3. Benchmark Results: 68% Efficiency Gain

We benchmarked traditional **Nested Agent Delegation** against **Pre-Routed Interception (with Ember Fast-Tier Interception)** using Gemini 3.5 Flash via ADK:

| Metric | Nested Agent Delegation | Pre-Routed Interception | Improvement |
| :--- | :--- | :--- | :--- |
| **Latency to Real Content** | 2.4s (silence during tool-call) | 2.7s (final answer streaming) | **Instant Streaming** |
| **Total Delivery Time** | 8.49s | 2.73s | **~3.1x Faster (68% Reduction)** |

---

## 4. Accuracy Optimization at the Edge

By employing **Hyper-Restrictive Prompting** and salience ordering, we boosted Meta Llama 3.1 8B's accuracy on an 11+ agent matrix by **200%** over standard baseline prompts.

### Core Technical Architecture Highlights

- **OpenTelemetry Standard**: Distributed tracing across FastAPI API calls and local model kernels.
- **KV-Cache Optimization**: Static system prompts guarantee hardware acceleration for repeated structures.
- **Structural Forcing**: GBNF grammar constraints for Llama.cpp and ChatML formatting hooks for Gemma and Mistral.
