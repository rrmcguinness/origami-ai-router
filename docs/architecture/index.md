# Origami AI Router Architectural Overview

## Executive Summary

The **Origami AI Router** is a high-performance, stateless API routing layer designed to sit at the edge of an enterprise AI agentic system. Its primary purpose is to orchestrate and decompose complex user prompts into an explicit **11-agent execution matrix** with sub-second latency while enforcing operational security pre-filtering against vector attacks. By decoupling initial routing logic and threat sanitization from stateful ADK execution nodes, the system achieves massive horizontal scalability while maintaining strict structural integrity and drastically reducing Time-To-Actual-Response (TTAR).

---

## Core Architecture

### 1. The 11-Agent Matrix

Origami AI Router replaces arbitrary multi-agent tool-calling architectures with a deterministic, pre-defined subset of agents tailored for holistic retail and customer service operations:

- `boring_basics_buyer`
- `culinary_wizard`
- `rule_book_nerd`
- `chaos_coordinator`
- `party_animal_planner`
- `retail_therapy_bot`
- `deets_detective`
- `swipe_right_advisor`
- `brainiac_supreme`
- `grease_monkey_genius`
- `dumpster_fire_handler`

### 2. Multi-Tiered AI Backend

The routing engine natively supports a dynamic cloud-to-edge hardware topology:

- **Operational Security Pre-Filter (`origami_ops_sec`)**: Intercepts queries before routing or LLM turn execution (`before_route`). Classifies vector attack patterns (`< 50ms`) across 5 categories and acts as a safe context intermediary (store-and-slim payload sanitization). For full implementation details, see [OpsSec Architecture](ops-sec.md).
- **Ember Fast-Tier**: Powered by `BAAI/bge-m3` via `sentence-transformers`. Evaluates pure cosine similarity at the Edge with sub-20ms latency and high RPS. Intercepts zero-shot intent classifications before they hit the LLM layer.
- **Cloud Primary**: `Gemini 3.5 Flash` (~95%+ Accuracy). Handles all high-throughput, latency-critical orchestration queries seamlessly via the Google Cloud backend that fail the Ember confidence threshold.
- **Offline Edge Fallbacks**: Dedicated local inference endpoints powered by `llama-cpp-python` executing 8B-12B quantized workflows (`Meta-Llama 3.1 8B`, `Gemma 3 12B`, and `Mistral NeMo 12B`). These fallback mechanisms provide zero-dependency routing at ~75% baseline accuracy when public cloud APIs are unreachable.

### 3. Strongly Typed Injection

Origami AI Router enforces strict dependency injection across its boundaries via a unified `Config` class, rather than relying on brittle dictionary definitions or implicit environment variables. This isolates target paths (`model_path`), rules configurations (`rules_routing`, `rules_ops_sec`), multi-threading parameters (`n_threads`), and provider allocations safely at initialization rather than runtime.

---

## Performance Enhancements

### 1. Asynchronous Pipelining & Decoupled Routing Engine
The core router engine runs on FastAPI, executing queries through an extensible `RoutingPipeline` (`OpsSecPreFilterStep`, `FastTierStep`, `TargetProviderStep`). This prevents connection starvation during high-concurrency bursts and scales to thousands of offline or cloud-bound throughput connections.

### 2. Callback Pre-Routing & OpsSec Sanitization (ADK Integration)
Origami AI Router hooks into the ADK's `before_agent_callback` and `before_model_callback`. Instead of wasting an expensive LLM turn to have an "Autonomous Coordinator" guess where to route the prompt or risk prompt injection poisoning, Origami AI Router intercepts the message, performs sub-50ms security sanitization and routing classification, and dynamically loads the sanitized instruction into the ADK session before inference begins.

### 3. Structural Forcing
Depending on the local fallback engine, Origami AI Router natively corrects systemic tokenizer behaviors:
- **Mistral & Llama**: Locked explicitly into `chatml` templates to map natively with prompt tuning.
- **Gemma**: Intercepts the underlying request to fold API system roles dynamically into standard user instructions, effectively bypassing Gemma's formatting vulnerabilities to recover over 40% accuracy immediately.

---

## Trade-off Analysis

| Feature         | Pros                                    | Cons                                                        |
| :-------------- | :-------------------------------------- | :---------------------------------------------------------- |
| **Performance** | Asynchronous single-turn TTAR boosts.   | Requires strict fallback rules for state modifications.     |
| **Cost**        | Vastly cheaper Flash/Small Model tokens.| Cloud latency introduces standard VPC network jitter.       |
| **Security**    | `before_route` vector attack pre-filtering & safe context intermediary. | Sub-50ms embedding similarity match introduces ~40ms overhead. |
| **Resilience**  | Hardened fallback to air-gapped models. | Edge models peak at ~75% accuracy without few-shot logic.   |
| **Scalability** | Endpoints are completely stateless.     | Adds an intentional API microservice hop to the sequence.   |
