# Meta Llama 3.1 8B Assessment Report

## Overview

Evaluates the zero-shot routing performance of Meta Llama 3.1 8B quantized weights executed locally via `origami_llama_cpp` with GBNF structural grammar forcing.

---

## Load Test Metrics

- **Total Requests**: 100
- **Successful Classifications**: 75
- **Failed Classifications**: 25
- **Load Generation Duration**: 45.62 seconds
- **Throughput (RPS)**: 2.19 RPS
- **Overall Accuracy**: **75%**

---

## Key Findings

1. **Format Reliability**: GBNF grammar rules guaranteed valid JSON response payloads on 100% of turns.
2. **Speed Baseline**: Fastest local execution speed (2.19 RPS) among local CPU models.
3. **Common Errors**: Demographic keywords pull intent toward `party_animal_planner`, and state modifications default to shopping commands rather than `fallback`.

---

## Recommendations

Selected as the **Primary Local Edge Fallback** backend for offline operation.
