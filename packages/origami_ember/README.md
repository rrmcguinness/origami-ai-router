# Origami AI Router - Ember Fast-Tier Package (`origami-ember`)

The `origami-ember` package implements an ultra-fast, local embedding-based intent interception router (`EmberRouter`) powered by `BAAI/bge-m3` via `sentence-transformers`.

It mathematically evaluates normalized cosine similarity to intercept unambiguous queries in **sub-20 milliseconds**, bypassing heavy generative LLM execution for high-frequency queries.

---

## Key Features

- **Per-Example Embedding Strategy**: Encodes agent descriptions and individual query examples separately into single-vector embeddings to prevent signal dilution.
- **Sub-20ms Interception**: High-throughput CPU/GPU similarity search returning intent classification and confidence scores.
- **Asymmetric Prefix Support**: Applies task-specific query instructions (e.g. `"Represent this sentence..."`) for enhanced vector alignment.
- **VRAM Isolation**: Automatically targets CUDA if available, falling back to CPU to prevent VRAM allocation conflicts on macOS.

---

## Installation

```bash
uv sync --package origami-ember
```

---

## Usage Example

```python
import asyncio
from origami_api.config import Config
from origami_api.models import RoutingRules
from origami_ember.router import EmberRouter

async def main():
    config = Config()
    rules = RoutingRules.from_toml_file("rules.toml")

    # Initialize EmberRouter with embedding weights
    router = EmberRouter(
        rules=rules,
        config=config,
        model_path="models/bge-m3"
    )

    # Execute intent classification
    user_query = "What is the return policy for electronics?"
    target_agent, confidence = await router.route_detailed(user_query)

    print(f"Routed to: {target_agent} (Confidence: {confidence:.4f})")

if __name__ == "__main__":
    asyncio.run(main())
```
