# EdgeRouter - vLLM Router Package

The `vllm-router` package provides high-throughput inference for open-source models (like Gemma) using the vLLM engine.

> [!WARNING]
> This package is designed for Linux environments with NVIDIA GPU support. It is not compatible with macOS.

## Features

- **High-Throughput Inference**: Leverages vLLM's PagedAttention and efficient batching.
- **CUDA Optimized**: Built for NVIDIA GPUs with broad model support.
- **Seamless Integration**: Implements standard `stateless-router` interfaces.

## Prerequisites

- **NVIDIA GPU**: Required for vLLM operations.
- **CUDA Toolkit**: Correct versions must be installed for compilation.
- **Linux OS**: Strictly Ubuntu/Debian or similar.

## Installation

This package is conditionally installed via `uv` based on the system platform:

```bash
# On a Linux machine
uv sync --extra vllm-router
```

## Usage

```python
from vllm_router.main import VllmRouter
from stateless_router.models import CompletionRequest

router = VllmRouter(config)
response = await router.complete(CompletionRequest(prompt="Hello vLLM!"))
```
