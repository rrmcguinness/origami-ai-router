# EdgeRouter Architectural & Performance Optimizations Log

This document tracks the comprehensive architectural shifts, performance optimizations, and infrastructure stabilizations applied to this project to transform it into a scalable, enterprise-grade generic routing platform.

---

## 1. Zero-Fat Chain of Thought (CoT) Routing
**Date:** March 2026

* **Original:** The `origami_api` shared models blindly requested `{"route": "AgentName"}`. Because LLMs are autoregressive, forcing them to guess the output enum without a distinct "scratchpad" generated erratic routing failures for highly contextual requests.
* **What Changed:** Injected a specialized JSON-embedded logic block exclusively into `GeminiRouter` requiring step-by-step reasoning (`"reasoning": "..."`) *before* extracting the route.
* **Outcome:** Massive bump in Cloud API routing intelligence (i.e. successfully decoding cross-domain intents), while actively and explicitly shielding the local Edge fallbacks (Llama / vLLM) from bearing the CoT latency burden. The system correctly isolates deep reflection to the Cloud.

## 2. Orchestration Loop Pruning (ADK)
**Date:** March 2026

* **Original:** The `RootCoordinator` agent built via the Google ADK forced the model to compute and generate a lengthy XML `<thinking>` block *before* initiating the `get_routing_decision` cross-function tool call. 
* **What Changed:** The XML `<thinking>` directive was entirely stripped from the `RootCoordinator` orchestration instructions.
* **Outcome:** The ADK now immediately delegates routing decisions backward to the backend JSON API (which natively provides the CoT reasoning boundary via its custom prompt). This completely slashed **~2-3 seconds** off the multi-agent turn execution by eliminating an entire upstream generation loop.

## 3. Shorthand CoT Compression & Token Capping
**Date:** March 2026

* **Original:** The initial JSON CoT block required grammatical reasoning sentences (e.g. *"If user asking about X, then route to Y because Z"*) which consumed ~40-50+ generated tokens, linearly increasing execution time. Furthermore, the Vertex AI `generation_config` lacked a hard boundary limit.
* **What Changed:** 
  1. Mandated the `"reasoning"` instruction to emit an ultra-brief, cryptic shorthand (`kwd:X->auto->Y`).
  2. Bolted a physical ceiling (`"max_output_tokens": 100`) directly into the Gemini generation configurations.
* **Outcome:** Successfully truncated token generation payloads to protect upstream execution scales. Pinned a mechanical boundary directly onto the API to violently halt runaway LLM hallucination cycles, securing a low Time-To-First-Route (TTFR) tax.

## 4. Rebranding & Package Decoupling (Origami Architecture)
**Date:** March 2026

* **Original:** The repository consisted of a single monolithic routing framework bound to proprietary client names, suffering from sprawling environment dependencies (mixing bare-metal PyTorch/CUDA with standard APIs).
* **What Changed:** A massive structural repository-wide namespace migration adopting the `origami` standard. The architecture was decoupled into standalone python packages: `origami-router`, `origami-gemini`, `origami-vllm`, `origami-llama-cpp`, `origami-api`, and `origami-common`. Included sanitizing proprietary data via destructive Git index filtering.
* **Outcome:** Achieved a highly portable, modular architecture. Complex environment targets like vLLM are now fully isolated from core API abstractions, heavily reducing CI/CD fragility and creating a clean open-source foundation.

## 5. Rigid Configuration-Driven Heuristics (Edge Stability)
**Date:** March 2026

* **Original:** Agent routes were defined using abstract, conversational paragraphs inside `rules.toml`. Edge-deployed models (like Llama 3.1 8B) hallucinated under the conceptual ambiguity. Validation tests relied on hardcoded python assertions which rapidly drifted from the underlying rule-set logic.
* **What Changed:** Overhauled `rules.toml` by migrating abstract instructions into rigid, action-oriented literal heuristics (e.g., mapping triggers directly to actions). Fully stripped python-hardcoded assertions offloading the entire test truth logic into `test_cases.toml`.
* **Outcome:** Solved persistent regression failures by grounding Edge layer local models into rigid reasoning boxes, significantly increasing zero-shot routing accuracy for smaller models. Created a single, non-code "Source of Truth" for QA validation.

## 6. OpenTelemetry (OTel) Standardization
**Date:** March 2026

* **Original:** Logging architectures used varied spans resulting in fragmented performance traces separating API calls from bare-metal local execution times.
* **What Changed:** Unified OpenTelemetry initialization logic globally. Synchronized distinct semantic attributes (e.g., `router.latency`, `router.outcome`, `router.environment`) precisely at the execution span layer across all implementation modules (`Gemini`, `llama_cpp`, `vLLM`).
* **Outcome:** Guaranteed identical, normalized determinism for enterprise observability. Tracing dashboards can seamlessly overlay Gemini Cloud scaling performance alongside bare-metal Llama execution times without attribute gaps.

## 7. Zero-Drift Hierarchical Configuration Overrides
**Date:** March 2026

* **Original:** The codebase relied on sprawling `os.environ.get()` statements and deprecated `get_test_env_setting` utilities, causing unpredictable initialization failures during test workflows vs server workflows.
* **What Changed:** Solidified dependency injection by moving all environment parsing to the heavily typed `origami_api.config.Config` class block. Built strict environment cascading to cleanly merge base `.env.toml` configurations with explicit `.env.test.toml` and `.env.local.toml` boundaries.
* **Outcome:** Created bulletproof application bootstrapping. Models, hyperparameters, and encrypted API keys are predictably resolved and injected recursively entirely eliminating `ValidationError` startup crashes.

## 8. Agent Salience & Context Prioritization
**Date:** March 2026

* **Original:** Agents were fed into the system prompt based on their arbitrary array order in the configuration file, causing LLM attention mechanisms to sometimes prioritize low-priority fallbacks (like trivia handlers) simply because of their string position.
* **What Changed:** Introduced a dynamic `salience: int` property to the core `AgentDefinition` Pydantic model. Before evaluating any routes, the `origami_api` automatically sorts all mapped agents in descending order based on their assigned salience score.
* **Outcome:** High-risk boundaries and safety nets (e.g. `dumpster_fire_handler` with `salience = 100`) are guaranteed to appear at the absolute top of the LLM context window. This directly exploits autoregressive attention bias, ensuring critical safety boundary rules are neurologically evaluated first.
