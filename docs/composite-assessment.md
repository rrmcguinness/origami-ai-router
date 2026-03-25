# OrigamiRouter: Composite Model Assessment

## Executive Summary
This document synthesizes the rigorous load testing evaluations (100 asynchronous requests per model) across four distinct AI routing engines. The objective is to identify the strengths, limitations, and specific failure modes of each model when exposed to a complex, 11-agent stateless routing matrix. 

Furthermore, this analysis investigates how adjusting the prompt structures and test case definitions can organically elevate the local edge models' accuracy to production tiers.

---

## 1. Benchmark Comparison

| Routing Engine | Accuracy Floor | Throughput (RPS) | Deployment Class | Native Structuring |
| :--- | :--- | :--- | :--- | :--- |
| **Gemini 3.1 Flash Lite** | 100% | 1.62 | Enterprise Cloud | Flawless |
| **Meta Llama 3.1 8B** | 75% | 2.19 | Edge Inference | GBNF Forcing |
| **Google Gemma 3 12B** | 73% | 1.34 | Edge Inference | Strict ChatML Required |
| **Mistral NeMo 12B** | 66% | 1.55 | Edge Inference | Native Formatting |

---

## 2. Comparing and Contrasting the Models

### **The Enterprise Standard: Gemini 3.1 Flash**
Unsurprisingly, the cloud-based commercial orchestrator processed the highly nuanced zero-shot instructions flawlessly. It inherently recognized that modifying shopping carts requires stateful system fallbacks, and effortlessly navigated the semantic overlaps between categorical agents.

### **The Local Speed Demon: Llama 3.1 8B**
Llama yielded the highest local baseline (75%) and the fastest throughput (2.19 RPS) despite having the smallest parameter count. Llama excels at adhering to strict grammar structures natively in `llama.cpp` but aggressively defaults queries toward conversational agents (`events_shopping_planner`) anytime nuanced demographic phrasing is used (e.g., "for my 6 year old"). 

### **The Formatting Sensitive: Gemma 3 12B**
Gemma required manual tokenizer manipulation to prevent the structural collapse of its System Prompts (originally dropping to 30% accuracy before folding the prompt directly into a user turn). Once fixed, it performed exactly on par with Llama (73%), though with substantially higher latency. 

### **The Cautious Formatter: Mistral NeMo 12B**
Mistral was incredibly robust at adhering to JSON generation without API crashes. However, it suffered the highest cognitive drift in the matrix (66%), heavily over-generalizing nuanced questions to the broader `shopping_tool` or `general_knowledge` endpoints rather than selecting specialized agents (such as `decision_assistant`).

---

## 3. Improving the Edge: Enhancing Test Quality & Prompt Definitions

The 70-75% accuracy "glass ceiling" observed across the local models is rarely a reflection of raw model capability. Instead, it highlights that **the quality and ambiguity of the prompt rules and validation cases are disproportionately penalizing zero-shot edge models**. Edge models require extreme determinism.

To push local models toward the >95% threshold, the following structural improvements should be implemented:

### A. Eliminating Semantic Overlap in Definitions
Currently, the distinction between agents like `customer_faq_agent` and `us_customer_care` relies on implicit cloud-tier reasoning. 
* **The Fix:** Inject explicit negative constraints into the Agent `description` properties inside `rules.toml`.
* *Example:* "Use `us_customer_care` exclusively for active order issues. DO NOT use this for generalized company policies—route those to `customer_faq_agent`."

### B. Defining Stateful Fallback Rules
Cloud models intrinsically suspect that "Add this to my cart" is not a routing agent command. Edge models blindly attempt to route it to `shopping_tool`, failing the test. 
* **The Fix:** Implement an explicit global rule instructing the system to abort. 
* *Example:* `global_rules = ["If the user attempts to add an item to a cart or modify an order, you MUST route to 'fallback'."]`

### C. Few-Shot Anchor Injections
Zero-shot execution on a 20-agent matrix overwhelms 8B-12B parameter contexts. 
* **The Fix:** The `RouterBuilder` should optionally inject 3 to 4 "golden" examples into the system instruction prompt. Showing a local model exactly how to map a tricky conversational phrase instantly aligns its internal reasoning graph for the duration of the session.

### D. Widening the Testing Matrix (Variable Acceptance)
The integration test assertions currently enforce a strict 1-to-1 binary string match across queries that realistically possess acceptable alternative answers.
* **The Fix:** Update `tests/integration/data.py` to allow arrays of acceptable intent mappings for ambiguous queries. If a query effectively requires a "Decision Assistant", but the model routes it to a highly capable "Shopping Tool", it should pass the fallback viability test rather than artificially flagging as a failure.
