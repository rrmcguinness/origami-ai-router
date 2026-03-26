# Origami AI Router: Gemma 3 12B Assessment Report

## Overview
This document evaluates the zero-shot routing accuracy of Google's local `Gemma 3 12B` instruction-tuned quantized weights (Q4_K_M) when utilized within the stateless Origami AI Router ecosystem. 

The evaluation simulates an enterprise load test of 100 concurrent/asynchronous routing scenarios across our full 11-agent complex matrix.

## Load Test Metrics (Async Throughput)
- **Total Requests**: 100
- **Successful Classifications**: 73
- **Failed Classifications**: 27
- **Load Generation Duration**: 74.74 seconds
- **Throughput (RPS)**: 1.34 Requests Per Second
- **Overall Accuracy**: **73%**

*Note: The test framework expects a strict >95% routing accuracy baseline.*

## Key Insights & Error Analysis
Initially, Gemma 3 completely collapsed under the standard prompt structure (acting as a "system" role), yielding only a 30% accuracy. However, after explicitly refactoring the `origami_llama_cpp` to fold the rigid JSON system taxonomy directly into the `user` turn, the model's structural grounding was restored and its accuracy shot up to **73%**—effectively tying the Meta Llama 3.1 8B model's performance (75%).

### Remaining Failure Patterns (The Local AI Glass Ceiling)
Even with strict prompt formatting corrected, the 12B model suffers from the same zero-shot limitations as all other quantized edge models when exposed to a massive 20-agent matrix without intermediate chain-of-thought processing:

1. **Subtle Intent Overlap**: 
   - `"What are some creative ways to use magnetic building toys?"` -> Routed to `brainiac_supreme` instead of `retail_therapy_bot`.
   - `"Are there any choking hazards for this play set for my 2 year old?"` -> Routed to `retail_therapy_bot` instead of `deets_detective`.
2. **Contextual Generalizations**:
   - Both Gemma and Llama tend to heavily favor `retail_therapy_bot` and `brainiac_supreme` as catch-all buckets when the nuance of the instruction set exceeds their zero-shot threshold.

## Strategic Recommendations
1. **Gemini 3.1 Flash Lite Excellence**: The cloud-based Gemini orchestrator remains the undisputed champion at **100% accuracy**. Until local hardware drastically improves, the cloud gateway is the only viable backend for strict multi-agent orchestration.
2. **Local Edge Fallbacks**: Llama 3.1 8B (75%) and Gemma 3 12B (73%) perform identically within the margin of error. However, Llama 3.1 8B processed the load test significantly faster (~20-25 seconds vs Gemma's 75 seconds). For edge deployments, **Llama 3.1 8B is the superior fallback option** simply due to its higher throughput/lower memory footprint at analogous accuracy.
