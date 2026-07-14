# Origami AI Router - `llama.cpp` Edge Package (`origami-llama-cpp`)

The `origami-llama-cpp` package provides offline, local edge LLM routing executing quantized GGUF models (Meta Llama 3.1 8B, Gemma 3 12B, Mistral NeMo 12B) via the `llama-cpp-python` C++ bindings.

---

## Key Features

- **Structural Grammar Forcing (GBNF)**: Guarantees 100% syntactically valid JSON output on every inference turn using strict context-free grammars.
- **Model-Specific Chat Templates**: Auto-detects model architectures (`llama-3`, `gemma`, `chatml`) and dynamically folds system prompts into user instructions when required to prevent structural collapse.
- **Hardware Acceleration**: Multi-threaded CPU execution with Apple Silicon Metal and Linux NVIDIA CUDA offloading (`n_gpu_layers=-1`).
- **Worker Pool Architecture**: Provides `LlamaCppWorkerPool` for multithreaded queue-based request distribution across local compute cores.

---

## Installation & Hardware Setup

For CUDA offloading on Linux:

```bash
export CUDACXX=/path/to/nvcc
CMAKE_ARGS="-DGGML_CUDA=on" uv pip install llama-cpp-python --reinstall --no-binary llama-cpp-python --no-cache-dir
```

---

## Usage Example

```python
import asyncio
from origami_api.config import Config, RouterConfig
from origami_api.models import RoutingRules
from origami_llama_cpp.main import LlamaCppRouter, LlamaCppRouterConfig

async def main():
    config = Config()
    rules = RoutingRules.from_toml_file("rules.toml")

    # Define router configuration
    llama_cfg = LlamaCppRouterConfig(
        model_path="models/llama-3.1-8b-instruct.Q4_K_M.gguf",
        n_threads=8
    )

    # Initialize local edge router
    router = LlamaCppRouter(rules=rules, config=llama_cfg)

    # Route request locally
    target_route = await router.route("Can you recommend a recipe for tonight?")
    print(f"Routed to: {target_route}")

    # Dispose of native bindings
    router.close()

if __name__ == "__main__":
    asyncio.run(main())
```
