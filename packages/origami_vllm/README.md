# Origami AI Router - vLLM Package (`origami-vllm`)

The `origami-vllm` package provides high-throughput, continuous-batching GPU inference for open-weights models (such as Gemma, Mistral, and Llama) backed by the `vllm.engine.async_llm_engine.AsyncLLMEngine`.

> [!IMPORTANT]
> This package requires a **Linux environment** with **NVIDIA CUDA GPU support**. It is not supported on macOS or Windows.

---

## Features

- **Continuous Batching & PagedAttention**: Achieves 500+ RPS throughput by dynamically batching concurrent requests without VRAM thrashing.
- **Guided Decoding**: Integrates regex-based guided decoding (`StructuredOutputsParams`) to enforce JSON schema formatting on every generated token.
- **Async Engine Integration**: Native non-blocking integration with `AsyncLLMEngine` for FastAPI and asynchronous multi-agent orchestrators.

---

## Installation

```bash
# On a Linux GPU machine
uv sync --package origami-vllm
```

---

## Configuration

In `.env.toml` or via explicit configuration:

```toml
[ai_models.vllm]
model_path = "models/gemma-3-12b-it"
```

---

## Usage Example

```python
import asyncio
from origami_api.config import Config
from origami_api.models import RoutingRules
from origami_vllm.main import VllmRouter, VllmRouterConfig

async def main():
    config = Config()
    rules = RoutingRules.from_toml_file("rules.toml")

    vllm_cfg = VllmRouterConfig(
        model_path="models/gemma-3-12b-it"
    )

    # Instantiate vLLM high-throughput router
    router = VllmRouter(rules=rules, config=vllm_cfg)

    # Route query
    target_route = await router.route("I need assistance with an auto care service.")
    print(f"Target Route: {target_route}")

if __name__ == "__main__":
    asyncio.run(main())
```
