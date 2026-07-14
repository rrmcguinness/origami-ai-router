# Mistral NeMo 12B Assessment Report

## Overview

Evaluates zero-shot routing accuracy of `Mistral NeMo 12B Instruct` quantized weights (Q4_K_M) running in local stateless mode.

---

## Load Test Metrics

- **Total Requests**: 100
- **Successful Classifications**: 66
- **Failed Classifications**: 34
- **Load Generation Duration**: 64.52 seconds
- **Throughput (RPS)**: 1.55 RPS
- **Overall Accuracy**: **66%**

---

## Key Findings

- Flawless JSON syntax compliance out of the box without template tweaking.
- Lower zero-shot classification accuracy (66%) due to defaulting nuanced queries to generic buckets (`retail_therapy_bot` / `brainiac_supreme`).

---

## Deployment Recommendation

Positioned behind Gemini 3.5 Flash, Llama 3.1 8B, and Gemma 3 12B in the edge fallback hierarchy.
