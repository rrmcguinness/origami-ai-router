# Composite Model Assessment & Benchmark

## Executive Summary

This document synthesizes load testing evaluations (100 asynchronous requests per model) across four AI routing backends. The objective is to evaluate accuracy, throughput, and structural stability across a complex 11-agent stateless routing matrix.

---

## Benchmark Metrics Comparison

| Routing Engine | Baseline Accuracy | Throughput (RPS) | Deployment Class | Structural Enforcement |
| :--- | :--- | :--- | :--- | :--- |
| **Gemini 3.5 Flash** | **100%** | 1.62 | Enterprise Cloud | Native JSON Schema |
| **Meta Llama 3.1 8B** | **75%** | 2.19 | Edge Inference | GBNF Grammars |
| **Google Gemma 3 12B** | **73%** | 1.34 | Edge Inference | Folded System Prompts |
| **Mistral NeMo 12B** | **66%** | 1.55 | Edge Inference | Native Formatting |

---

## Comparative Model Analysis

### Enterprise Cloud: Gemini 3.5 Flash
Commercial cloud orchestrator processing zero-shot instructions flawlessly (100% accuracy). Effortlessly parses subtle intent boundaries and stateful fallback triggers without requiring prompt tuning or few-shot examples.

### Local Speed Baseline: Llama 3.1 8B
Yielded the highest local baseline (75%) and fastest throughput (2.19 RPS) despite its smaller size. Excels at GBNF grammar adherence in `llama.cpp`, though tends to default demographic phrasing to `party_animal_planner`.

### Formatting Sensitivity: Gemma 3 12B
Required custom system prompt folding (moving instructions directly into the `user` turn) to recover accuracy from 30% to 73%. Demonstrates solid reasoning performance once formatting vulnerabilities are handled.

### Deterministic Formatter: Mistral NeMo 12B
Extremely reliable JSON generation without API crashes. Suffered higher cognitive drift (66%) by over-generalizing granular questions to `retail_therapy_bot` or `brainiac_supreme`.

---

## Remediation Paths for Edge Deployment (>95% Goal)

1. **Negative Constraints**: Add explicit negative heuristics into `rules.toml` (e.g., *"DO NOT route general policy queries to chaos_coordinator"*).
2. **Global Fallback Rules**: Enforce global rules for cart additions and stateful state modifications.
3. **Few-Shot Injections**: Provide 3-4 golden example pairs in `rules.toml` to guide local 8B-12B model attention mechanisms.
4. **Widen Test Case Arrays**: Accept valid alternative specialist classifications for ambiguous test cases.
