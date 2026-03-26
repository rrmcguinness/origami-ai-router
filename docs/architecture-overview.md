# Origami AI Router Architectural Overview

## Executive Summary

The **Origami AI Router** is a high-performance, stateless API routing layer designed to sit at the "edge" of an enterprise AI agentic system. Its primary purpose is to orchestrate and decompose complex user prompts into an explicit **11-agent execution matrix** with sub-second latency. By decoupling initial routing logic from stateful ADK execution nodes, the system achieves massive horizontal scalability while maintaining strict structural integrity and drastically reducing Time-To-Actual-Response (TTAR).

## Core Architecture

### 1. The 11-Agent Matrix
Origami AI Router replaces arbitrary multi-agent tool-calling architectures with a deterministic, pre-defined subset of agents tailored for holistic retail and customer service operations:
- `boring_basics_buyer`, `culinary_wizard`, `rule_book_nerd`, `chaos_coordinator`, `party_animal_planner`, `retail_therapy_bot`, `deets_detective`, `swipe_right_advisor`, `brainiac_supreme`, `grease_monkey_genius`, and `dumpster_fire_handler`.

### 2. Multi-Tiered AI Backend
The routing engine natively supports a dynamic cloud-to-edge hardware topology:
- **Ember Fast-Tier**: Powered by `BAAI/bge-m3` via `sentence-transformers`. Evaluates pure cosine similarity at the Edge with sub-20ms latency and high RPS. Intercepts zero-shot intent classifications before they hit the LLM layer.
- **Cloud Primary**: `Gemini 3.1 Flash Lite` (~95%+ Accuracy). Handles all high-throughput, latency-critical orchestration queries seamlessly via the Google Cloud backend that fail the Ember confidence threshold.
- **Offline Edge Fallbacks**: Dedicated local inference endpoints powered by `llama-cpp-python` executing 8B-12B quantized workflows (`Meta-Llama 3.1 8B`, `Gemma 3 12B`, and `Mistral NeMo 12B`). These fallback mechanisms provide zero-dependency routing at ~75% baseline accuracy when public cloud APIs are unreachable.

### 3. Strongly Typed Injection
Origami AI Router enforces strict dependency injection across its boundaries via a unified `Config` class, rather than relying on brittle dictionary definitions or implicit environment variables. This isolates target paths (`model_path`), multi-threading parameters (`n_threads`), and provider allocations safely at initialization rather than runtime.

---

## Performance Enhancements

### 1. Asynchronous Pipelining
The core router engine (`src/origami-router/main.py`) runs on FastAPI, strictly enforcing `async`/`await` primitives down through the ADK integrations. This prevents connection starvation during high-concurrency bursts and easily scales to thousands of offline or cloud-bound throughput connections.

### 2. Callback Pre-Routing (ADK Integration)
Origami AI Router implements a distinct latency advantage by hooking into the ADK's `before_agent_callback`. Instead of wasting an expensive LLM turn to have an "Autonomous Coordinator" guess where to route the prompt, the Origami AI Router intercepts the message instantly, performs a sub-second API classification, and dynamically loads the target `instruction` directly into the current ADK session before the primary inference execution starts (reducing user wait times by ~50%).

### 3. Structural Forcing
Depending on the local fallback engine, Origami AI Router natively corrects systemic tokenizer behaviors:
- **Mistral & Llama**: Locked explicitly into `chatml` templates to map natively with prompt tuning.
- **Gemma**: Intercepts the underlying request to fold API system roles dynamically into standard user instructions, effectively bypassing Gemma's formatting vulnerabilities to recover over 40% accuracy immediately.

---

## Pros and Cons

| Feature         | Pros                                    | Cons                                                        |
| :-------------- | :-------------------------------------- | :---------------------------------------------------------- |
| **Performance** | Asynchronous single-turn TTAR boosts.   | Requires strict fallback rules for state modifications.     |
| **Cost**        | Vastly cheaper Flash/Small Model tokens.| Cloud latency introduces standard VPC network jitter.       |
| **Resilience**  | Hardened fallback to air-gapped models. | Edge models peak at ~75% accuracy without few-shot logic.   |
| **Scalability** | Endpoints are completely stateless.     | Adds an intentional API microservice hop to the sequence.   |

---

## Critical Analysis & Blindspots

### 1. The "Context Blindness" Trap

Because this router is **Locally Stateless**, it possesses no inherent memory of the last three ADK session turns. If a user asks a follow-up like *"Tell me more about that second one,"* a 100% stateless router model lacks the capability to know what "that" refers to.
- **Mitigation**: Origami AI Router natively accepts a `context_summary` payload alongside the immediate prompt, seamlessly condensing and injecting relevant multi-turn historical variables into the routing decision layer without needing the massive overhead of a continuous KV-cache.

### 2. The Local Model "Glass Ceiling"

Using 8B or 12B quantized models identically to a 1-Trillion parameter enterprise model inherently limits its nuanced cognitive reasoning. Complex edge routing prompts natively struggle to differentiate between adjacent definitions (e.g., separating standard explicit policy queries `rule_book_nerd` from human escalation logic `chaos_coordinator`). 
- **Mitigation**: The Origami AI Router requires explicit negative constraints to be written into the `rules.toml` structure, forcing smaller LLMs away from overlapping intents (or relying on Few-Shot injected prompts).

### 3. Scaling Constraints (Local Fallback)
While the `async` integration and Gemini Flash architectures handle infinite concurrent connection pipelines, dropping into the `auto_local` (llama.cpp) fallback architecture introduces strict hardware limitations. Local Python bindings allocate thread locks around memory kernels; massive sudden spikes (100+ concurrent requests) directed exclusively to the local edge cluster risk queue saturation and memory thrashing if the `threadPoolSize` exceeds the available silicon cores.
