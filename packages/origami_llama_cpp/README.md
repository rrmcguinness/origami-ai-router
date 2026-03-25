# OrigamiRouter - llama.cpp Router Package

The `origami-llama-cpp` package provides local LLM inference via the `llama-cpp-python` bindings. It is optimized for cross-platform support (macOS Apple Silicon and Linux CUDA).

## Features

- **Local Model Execution**: Run GGUF models locally on your workstation or edge device.
- **Metal & CUDA Support**: Hardware acceleration on macOS (Metal) and Linux (CUDA).
- **Fast Development Cycle**: Ideal for testing and development without cloud costs.
- **Stateless Router Compliance**: Adheres to the core routing standards.

## Installation

For GPU support, specific installation flags are required. See the [CUDA Setup Guide](../../docs/CUDA_SETUP.md) for more details.

```bash
# Standard installation
uv sync

# Force CUDA compilation
CUDACXX=/path/to/nvcc uv pip install --no-cache-dir llama-cpp-python
```

## Usage

```python
from origami_llama_cpp.main import LlamaCppRouter
from origami_stateless.models import CompletionRequest

router = LlamaCppRouter(config)
response = await router.complete(CompletionRequest(prompt="Hello llama.cpp!"))
```

## Testing

This router is frequently used for local integration tests and performance benchmarks. See the `tests/` directory for examples of how to configure and run tests with this router.
