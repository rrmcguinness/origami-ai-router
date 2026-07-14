# Origami AI Router - Stateless Router Package (`origami-stateless`)

The `origami-stateless` package provides the design pattern abstractions, fluent builder utilities, and provider-agnostic factories for constructing `StatelessRouter` instances.

---

## Key Modules & Classes

- **`origami_stateless.builder`**:
  - `RouterBuilder`: Fluent builder pattern for constructing `StatelessRouter` instances with provider classes, configurations, rules, and shared thread pools.

---

## Architecture Pattern

This package decouples provider-specific backend logic (Gemini, Llama.cpp, vLLM, Ember) from system setup. Swapping inference engines requires modifying only the provider registration parameter in the builder pipeline.

---

## Usage Example

```python
from concurrent.futures import ThreadPoolExecutor
from origami_api.config import Config
from origami_api.models import RoutingRules
from origami_gemini.main import GeminiRouter
from origami_stateless.builder import RouterBuilder

# 1. Initialize configuration and rules
config = Config()
rules = RoutingRules.from_toml_file("rules.toml")
executor = ThreadPoolExecutor(max_workers=8)

# 2. Build router using the fluent Builder pattern
router = (
    RouterBuilder()
    .with_provider(GeminiRouter, config=config)
    .with_rules(rules)
    .with_executor(executor)
    .build()
)

# 3. Router is ready for async execution
```
