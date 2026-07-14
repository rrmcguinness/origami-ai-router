# Gemma 3 12B Assessment Report

## Overview

Evaluates the zero-shot routing accuracy of Google's local `Gemma 3 12B` instruction-tuned quantized weights (Q4_K_M) within `origami_llama_cpp`.

---

## Load Test Metrics

- **Total Requests**: 100
- **Successful Classifications**: 73
- **Failed Classifications**: 27
- **Load Generation Duration**: 74.74 seconds
- **Throughput (RPS)**: 1.34 RPS
- **Overall Accuracy**: **73%**

---

## Technical Insights

- **System Prompt Folding**: Standard system roles caused structural collapse (30% baseline). Folding system context directly into user instructions elevated accuracy to **73%**.
- **Error Modes**: Over-generalization to `retail_therapy_bot` and `brainiac_supreme` on ambiguous prompts.

---

## Deployment Recommendation

Suitable as a secondary edge fallback. For CPU/memory constrained edge deployments, Llama 3.1 8B is preferred due to lower latency at comparable accuracy.
