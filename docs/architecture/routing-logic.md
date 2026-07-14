# Routing Logic & Engine Analysis

## Overview

As part of the Origami AI Router architectural refactor to inject model configurations dynamically from the control plane, comprehensive load testing was conducted against the `test_cases.toml` ground truth dataset.

This document records the baseline accuracy achieved using the refined agent instructions and details non-deterministic behavior observed during evaluations.

---

## Benchmark Accuracy Summary

### Gemini 3.5 Flash
- **Target Accuracy:** >95%
- **Achieved Accuracy:** 94% (94 Passed, 6 Failed)
- **Status:** Architecture verified. The required model configurations, including `thinking_config`, successfully load without errors.

### LlamaCpp (Local Edge)
- **Achieved Accuracy:** 72% (72 Passed, 28 Failed)
- **Status:** Functional, but lags behind Gemini in handling nuanced categorizations, particularly those involving newly structured agent instructions.

---

## Analysis of Gemini Non-Determinism ("Flip-Flops")

Despite achieving high baseline accuracy, the Gemini router demonstrated a minor degree of non-determinism across successive test runs. Specifically, 6 out of 100 queries "flipped" their classifications between runs, indicating statistical ties in probability distribution between conceptually overlapping agents.

### Observed Flip-Flops & Intent Boundaries

1. **Query:** `"I want something with tomatoes and cheese tonight."`
   - **Flipped Between:** `retail_therapy_bot` and `culinary_wizard`
   - **Reasoning:** Highly ambiguous intent. Leans toward ingredient-based meal formulation (`culinary_wizard`), but broadly asking for "something" could also imply ready-made foods or groceries (`retail_therapy_bot`).

2. **Query:** `"I can't decide what to eat for dinner"`
   - **Flipped Between:** `retail_therapy_bot` and `culinary_wizard`
   - **Reasoning:** User asks for dinner inspiration, blurring the line between shopping for grocery items vs recipe synthesis.

3. **Query:** `"Can I get a tire rotation and oil change at the same time at Retailer?"`
   - **Flipped Between:** `fallback` and `grease_monkey_genius`
   - **Reasoning:** Ground truth sets this to `dumpster_fire_handler` (general routing), but explicit mentions of "tire rotation" and "oil change" strongly pull attention mechanisms toward `grease_monkey_genius`.

4. **Query:** `"What do I need to buy for tonight?"`
   - **Flipped Between:** `retail_therapy_bot` and `party_animal_planner`
   - **Reasoning:** "Tonight" implies a time-bound event (`party_animal_planner`), while "buy" anchors it to generic shopping functionality (`retail_therapy_bot`).

5. **Query:** `"Is this a good investment?"`
   - **Flipped Between:** Ambiguous classification impacting `swipe_right_advisor` when visual context is missing.

---

## Remediations & Action Items

If 94% accuracy with minor non-determinism requires mitigation for strict production loads:

1. **Greedy Temperature Decoding:** Ensure model temperature is set to `0.0` within `.env.toml` to force greedy, deterministic decoding.
2. **Instruction Hardening:** Provide explicit negative-boundary prompts in `rules.toml` (e.g., *"If the user is vaguely asking what to eat for dinner WITHOUT specifying ingredients to cook, route to retail_therapy_bot instead of culinary_wizard"*).
