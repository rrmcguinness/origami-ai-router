# Accuracy Benchmarking Report: EdgeRouter Local Models

This report compares the performance of **Gemma 3 4B-IT** vs. **Meta-Llama-3.1-8B-IT (GGUF)** in a retail-specific routing task involving 20+ specialized agents.

## Executive Summary 

| Model | Strategy | Accuracy | Status |
| :--- | :--- | :--- | :--- |
| **Gemini 3.1 Flash Lite** | Golden Standard | **~96%** | **PASSED** |
| **Llama 3.1 8B** | **Phase 5: Hyper-Restrictive** | **65.9%** | **PASSED** |
| **Gemma 4B** | Standard Prompt | **~22%** | **FAILED** |

> [!IMPORTANT]
> While Gemini 3.1 Flash Lite remains the "Golden Standard" for accuracy, Llama 3.1 8B achieved a **200% improvement** over the Gemma 4B baseline, successfully breaking the 60% target for decentralized edge routing.

---

## Detailed Comparison 

### Top Wins (Llama 3.1 8B)
Llama 3.1 8B correctly classified complex test cases that Gemma mapped incorrectly:
1. **Nuanced Intent**: "birthday party" ➡️ `EventsPlanner` (Gemma misclassified this as `InternationalShipping`).
2. **Safety Boundaries**: "What is the return policy ?" ➡️ `OrderSupport` (Llama correctly identified the intent despite the filler).
3. **Structured Logic**: Llama adhered to the **Hyper-Restrictive HARD RULES** which prevented it from deviating from the routing target.

### Critical Failures & Insights
- **Gemma 4B**: Suffered from classification confusion with 20+ categories. It defaulted heavily to `ShoppingTool` or `Fallback` for anything remotely complex.
- **Llama 3.1 8B**: Still struggles occasionally with the boundary between `Fallback` (Cart Modification) and `OrderSupport` (Order lifecycle) due to shared terminology like "order" and "substitutions."

## Strategy Breakthrough: Hyper-Restrictive Prompting 

The leap from 46% (Phase 4) to 65.9% (Phase 5) was driven by:
- **Salience Prioritization**: Moving Fallback and OrderSupport rules to the front of the context.
- **Negative Constraints**: A "Traffic Controller" persona that strictly forbids conversational filler.
- **Command-Style Instructions**: Switching from descriptions ("Use this for...") to hard conditionals ("IF query is X -> route to Y").

---

## Conclusion 
**Llama 3.1 8B is the recommended edge model for the Retailer EdgeRouter.**  It provides the necessary parameter density to handle the current 25+ agent matrix with acceptable production accuracy. 
