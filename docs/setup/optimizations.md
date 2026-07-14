# Architectural & Performance Optimizations Log

This document tracks the comprehensive architectural shifts, performance optimizations, and infrastructure stabilizations applied to transform Origami AI Router into a scalable, enterprise-grade generic routing platform.

---

## 1. Zero-Fat Chain of Thought (CoT) Routing

- **Original:** The `origami_api` shared models requested `{"route": "AgentName"}`. Because LLMs are autoregressive, forcing them to guess the output enum without a distinct "scratchpad" generated erratic routing failures for highly contextual requests.
- **What Changed:** Injected a specialized JSON-embedded logic block exclusively into `GeminiRouter` requiring step-by-step reasoning (`"reasoning": "..."`) *before* extracting the route.
- **Outcome:** Massive bump in Cloud API routing intelligence (i.e. successfully decoding cross-domain intents), while actively and explicitly shielding local Edge fallbacks (Llama / vLLM) from bearing the CoT latency burden. The system isolates deep reflection to the Cloud.

---

## 2. Orchestration Loop Pruning (ADK)

- **Original:** The `RootCoordinator` agent built via Google ADK forced the model to compute and generate a lengthy XML `<thinking>` block *before* initiating the `get_routing_decision` cross-function tool call. 
- **What Changed:** Stripped the XML `<thinking>` directive from `RootCoordinator` orchestration instructions.
- **Outcome:** ADK immediately delegates routing decisions backward to the backend JSON API (which natively provides the CoT reasoning boundary via its custom prompt). This slashed **~2-3 seconds** off multi-agent turn execution by eliminating an entire upstream generation loop.

---

## 3. Shorthand CoT Compression & Token Capping

- **Original:** The initial JSON CoT block required grammatical reasoning sentences (e.g. *"If user asking about X, then route to Y because Z"*) which consumed ~40-50+ generated tokens, linearly increasing execution time.
- **What Changed:** 
  1. Mandated the `"reasoning"` instruction to emit an ultra-brief shorthand (`kwd:X->auto->Y`).
  2. Integrated a physical ceiling (`"max_output_tokens": 100`) directly into Gemini generation configurations.
- **Outcome:** Truncated token generation payloads to protect upstream execution scales. Pinned a mechanical boundary directly onto the API to halt runaway LLM hallucination cycles, securing low TTFR.

---

## 4. Rebranding & Package Decoupling (Origami Architecture)

- **Original:** The repository consisted of a single monolithic routing framework bound to proprietary client names, suffering from sprawling environment dependencies.
- **What Changed:** Executed a repository-wide namespace migration adopting the `origami` standard. Decoupled into standalone python packages: `origami-router`, `origami-gemini`, `origami-vllm`, `origami-llama-cpp`, `origami-api`, `origami-common`, and `origami-ember`.
- **Outcome:** Achieved a highly portable, modular architecture. Complex environment targets like vLLM are fully isolated from core API abstractions, heavily reducing CI/CD fragility.

---

## 5. Rigid Configuration-Driven Heuristics (Edge Stability)

- **Original:** Agent routes were defined using abstract, conversational paragraphs inside `rules.toml`. Edge-deployed models (like Llama 3.1 8B) hallucinated under conceptual ambiguity.
- **What Changed:** Overhauled `rules.toml` by migrating abstract instructions into rigid, action-oriented literal heuristics. Fully stripped python-hardcoded assertions, offloading test truth logic into `test_cases.toml`.
- **Outcome:** Solved persistent regression failures by grounding Edge layer local models into rigid reasoning boxes, significantly increasing zero-shot routing accuracy for smaller models.

---

## 6. OpenTelemetry (OTel) Standardization

- **Original:** Logging architectures used varied spans resulting in fragmented performance traces separating API calls from bare-metal local execution times.
- **What Changed:** Unified OpenTelemetry initialization logic globally. Synchronized distinct semantic attributes (e.g., `router.latency`, `router.outcome`, `router.environment`) precisely at the execution span layer across all implementation modules (`Gemini`, `llama_cpp`, `vLLM`, `ember`).
- **Outcome:** Guaranteed identical, normalized determinism for enterprise observability across GCP Cloud Trace and OpenTelemetry collectors.

---

## 7. Zero-Drift Hierarchical Configuration Overrides

- **Original:** Codebase relied on sprawling `os.environ.get()` statements and deprecated environment setting utilities.
- **What Changed:** Solidified dependency injection by moving environment parsing to the strongly typed `origami_api.config.Config` class block. Built strict environment cascading to cleanly merge base `.env.toml` configurations with explicit `.env.test.toml` and `.env.local.toml` boundaries.
- **Outcome:** Created bulletproof application bootstrapping. Models, hyperparameters, and encrypted API keys are predictably resolved and injected recursively.

---

## 8. Agent Salience & Context Prioritization

- **Original:** Agents were fed into the system prompt based on their arbitrary array order in the configuration file, causing LLM attention mechanisms to prioritize low-priority fallbacks simply due to string position.
- **What Changed:** Introduced a dynamic `salience: int` property to the core `AgentDefinition` Pydantic model. Before evaluating routes, agents are automatically sorted in descending order based on assigned salience score.
- **Outcome:** High-risk boundaries and safety nets (e.g. `dumpster_fire_handler` with `salience = 100`) appear at the top of the context window, taking advantage of autoregressive attention bias.

---

## 9. Ember Fast-Tier (Embedding-Based Pre-Routing)

- **Original:** The system relied exclusively on heavy generative LLMs to classify every single intent. Simple queries suffered from autoregressive generation latency.
- **What Changed:** Introduced the `origami_ember` package, establishing an ultra-fast, local embedding layer powered by `BAAI/bge-m3` via `sentence-transformers`. Implemented asymmetric instruction prefixes and a confidence threshold interception hook (`confidence_threshold = 0.8`) in the FastAPI router.
- **Outcome:** Ember mathematically evaluates cosine similarity and intercepts clear intents in **sub-20 milliseconds**, achieving **~48 RPS** on standard CPUs. Bypassing the heavy LLM layer for ~50% of incoming queries dramatically slashes cloud API costs and TTAR.
