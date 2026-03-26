# Origami AI Router: Mistral NeMo 12B Assessment Report

## Overview
This document evaluates the zero-shot routing accuracy of the `Mistral NeMo 12B Instruct` quantized weights (Q4_K_M) when run natively inside the local stateless Origami AI Router execution pool. 

The evaluation simulates an enterprise load configuration by firing 100 concurrent/asynchronous routing requests targeting the fully expanded 11-agent complex matrix. 

## Load Test Metrics (Async Throughput)
- **Total Requests**: 100
- **Successful Classifications**: 66
- **Failed Classifications**: 34
- **Load Generation Duration**: 64.52 seconds
- **Throughput (RPS)**: 1.55 Requests Per Second
- **Overall Accuracy**: **66%**

*Note: The test framework strictly expects >95% routing accuracy to qualify as a primary routing engine.*

## Key Insights & Error Analysis
Mistral fundamentally succeeded in outputting clean JSON structures without systemic API or grammar failures. It was the only local model that never crashed or threw a schema validation error natively off the bat. However, its overall zero-shot cognitive capability on complex orchestration leveled out at a disappointing 66% (slightly below Llama 3.1 8B's 75% and Gemma 3 12B's 73%).

### Subtle Intent Misalignments
Mistral consistently struggled with highly granular product nuance, tending to default to the path of least resistance:
- `"Are there any choking hazards for this play set for my 2 year old?"` -> Got: `retail_therapy_bot` (Expected: `deets_detective`).
- `"show me some food options for party snacks"` -> Got: `retail_therapy_bot` (Expected: `party_animal_planner`).
- `"How do different types of juicers compare in terms of ease of use and cleaning?"` -> Got: `brainiac_supreme` (Expected: `retail_therapy_bot`).

### Structural Prompts Supported 
Unlike the Gemma load tests, Mistral NeMo was immediately responsive to `user`-injected structural system instructions (when passed natively as ChatML or dynamically folded strings). It recognized its JSON constraints flawlessly but lacked the pure analytical capability to identify edge-cases across 20 potential routing buckets in a single prompt evaluation. 

## Strategic Conclusion
The **Mistral NeMo 12B** engine is remarkably stable for returning deterministic formatting strings, but its 66% zero-shot accuracy restricts it from being utilized safely in production as a primary router. 

### Final Edge Hierarchy
Unless massive multi-shot or chain-of-thought methodologies are employed to walk the respective models through reasoning matrices, local quantized inferences are capped beneath a ~75% glass ceiling:
1. **Gemini 3.1 Flash Lite (Enterprise Cloud)** - 100% Accuracy (Primary Router)
2. **Llama 3.1 8B Local** - 75% Accuracy (Offline Edge Fallback)
3. **Gemma 3 12B Local** - 73% Accuracy 
4. **Mistral NeMo 12B Local** - 66% Accuracy
