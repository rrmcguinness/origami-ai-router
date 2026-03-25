# EdgeRouter: Llama Model Assessment Report

## Overview
This document evaluates the zero-shot routing accuracy of local Llama models (e.g., Llama 3 8B) when utilized within the stateless EdgeRouter ecosystem. 

The evaluation simulates a high-concurrency enterprise load test of 100 random routing scenarios across a complex 11-agent matrix, including nuanced intents like `shopping_tool`, `events_shopping_planner`, `decision_assistant`, and `recipe_agent`.

## Load Test Metrics (Async Throughput)
- **Total Requests**: 100
- **Successful Classifications**: 75
- **Failed Classifications**: 25
- **Load Generation Duration**: 45.62 seconds
- **Throughput (RPS)**: 2.19 Requests Per Second
- **Overall Accuracy**: **75%**

*Note: The test framework expects a strict 95% routing accuracy baseline, causing the automated load tests to fail under the current zero-shot conditions without few-shot tuning.*

## Key Insights & Error Analysis
While the local Llama model achieved reliable and quick JSON validation via structural forcing (GBNF Grammars), it struggled to distinguish between highly adjacent intents that the standard Gemini 3.1 Flash Lite model naturally isolates. 

Below are the most consistent classification failure patterns observed during the sweep:

### 1. General Product vs. Event Planning
Llama aggressively classified any product-related prompt with *demographic* or *gift* context into `events_shopping_planner` rather than recognizing it as a generalized `shopping_tool` query.
- `"I’m looking for a mother’s day gift but she hates knitting"` -> Got: `events_shopping_planner` (Expected: `shopping_tool`)
- `"Boy"` -> Got: `events_shopping_planner` (Expected: `shopping_tool`)
- `"Mediterranean brunch boards."` -> Got: `events_shopping_planner` (Expected: `shopping_tool`)
- `"Looking for unicorn themed gifts for 6 year old"` -> Got: `events_shopping_planner` (Expected: `shopping_tool`)

### 2. General FAQ vs. Detailed Context Support
Llama often confused generalized support questions with specific active-document inquiries.
- `"What if I want to return it? Is there a return policy?"` -> Got: `customer_faq_agent` (Expected: `decision_assistant`)
- `"Could you tell me about the seller's reviews for the Alienware m16?"` -> Got: `customer_faq_agent` (Expected: `carousel_qna`)
- `"Can I use coupons?"` -> Got: `customer_faq_agent` (Expected: `us_customer_care`)

### 3. Cart Actions Missing Fallback
In our architecture, modifying active user state (cart/list additions) must either be directed to a stateful orchestrator or delegated to `fallback` when running statelessly. Llama consistently tried to fulfill the command creatively.
- `"add the second one"` -> Got: `shopping_tool` (Expected: `fallback`)
- `"yes add them to my list"` -> Got: `essentials` (Expected: `fallback`)
- `"add it to my cart please"` -> Got: `shopping_tool` (Expected: `fallback`)

## Strategic Recommendations
Achieving >95% accuracy on an 8B edge model for an 11+ complex agent matrix is fundamentally unrealistic without applying one of the following remediation paths:

1. **Lower Thresholds for Local Testing:** If Llama is strictly a fallback for connectivity issues or basic interactions, drop the Pytest assertion from `0.95` to `0.70` to respect its isolated capabilities.
2. **Contextual Few-Shot Injection:** Embed 2-3 negative examples directly into the global system instruction (e.g., *"If the user asks to add something to their cart, MUST output fallback"*).
3. **Allow Matrix Variances:** Widen the acceptance criteria in `data.py` so that adjacent intents (like `customer_faq_agent` and `us_customer_care`) are scored interchangeably during basic local evaluations.
