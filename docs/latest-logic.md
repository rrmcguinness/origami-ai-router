# Integration Test Results & Routing Logic Analysis
Last Updated: March 24, 2026

## Overview
As part of the Origami AI Router architectural refactor to inject model configurations dynamically from the control plane, comprehensive load testing was conducted against the `test_cases.toml` ground truth dataset.

This document records the baseline accuracy achieved using the refined agent instructions and details the non-deterministic behavior observed during the evaluation.

## Test Results

### Gemini 2.5 Flash Lite
- **Target Accuracy:** >95%
- **Achieved Accuracy:** 94% (94 Passed, 6 Failed)
- **Status:** Architecture verified. The required model configurations, including `thinking_config`, successfully load without 404 errors. 

### LlamaCpp (Local)
- **Achieved Accuracy:** 72% (72 Passed, 28 Failed)
- **Status:** Functional, but lags significantly behind Gemini in handling nuanced categorizations, particularly those involving newly structured agent instructions.

## Analysis of Gemini "Flip-Flops" (Non-Determinism)

Despite achieving high accuracy, the Gemini router demonstrated a minor degree of non-determinism across successive test runs. Specifically, 6 out of 100 queries "flipped" their classifications between runs, indicating statistical ties in probability distribution between conceptually overlapping agents.

### Observed Flip-Flops

1. **Query:** `"I want something with tomatoes and cheese tonight."`
   - **Flipped Between:** `retail_therapy_bot` and `culinary_wizard`
   - **Reasoning:** A highly ambiguous intent. It leans toward ingredient-based meal formulation (`culinary_wizard`), but broadly asking for "something" could also imply ready-made foods or groceries (`retail_therapy_bot`).

2. **Query:** `"I can't decide what to eat for dinner"`
   - **Flipped Between:** `retail_therapy_bot` and `culinary_wizard`
   - **Reasoning:** Similar to the above. The user is asking for dinner inspiration, merging the line between shopping for dinner goods and producing a recipe.

3. **Query:** `"Can I get a tire rotation and oil change at the same time at Retailer?"`
   - **Flipped Between:** `fallback` and `grease_monkey_genius`
   - **Reasoning:** The ground truth sets this to `dumpster_fire_handler` (general routing), but the explicit mention of "tire rotation" and "oil change" strongly pulls the attention mechanisms toward the specialized `grease_monkey_genius` agent.

4. **Query:** `"What do I need to buy for tonight?"`
   - **Flipped Between:** `retail_therapy_bot` and `party_animal_planner`
   - **Reasoning:** "Tonight" implies a time-bound event or routine (`party_animal_planner`), but "buy" strongly anchors it to generic shopping functionality (`retail_therapy_bot`).

5. **Query:** `"Is this a good investment? "`
   - **Flipped Between:** Unpredictable classification heavily impacting `swipe_right_advisor` when visual context is stripped.

### Action Items & Next Steps

If 94% accuracy with minor non-determinism is unacceptable for production loads, the following adjustments can be made:
1. **Temperature Tuning:** Ensure the Vertex AI model temperature is set to `0.0` or as close to zero as possible within `.env.toml` to force greedy, deterministic decoding. 
2. **Instruction Hardening:** Provide explicit negative-boundary prompts in `routing_rules.py` (e.g., "If the user is vaguely asking what to eat for dinner WITHOUT specifying ingredients to cook, route to retail_therapy_bot instead of culinary_wizard").
