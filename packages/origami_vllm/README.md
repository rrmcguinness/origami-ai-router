# Origami AI Router - vLLM Router Package

The `origami-vllm` package provides high-throughput inference for open-source models (like Gemma) using the vLLM engine.

> [!WARNING]
> This package is designed for Linux environments with NVIDIA GPU support. It is not compatible with macOS.

## Features

- **High-Throughput Inference**: Leverages vLLM's PagedAttention and efficient batching.
- **CUDA Optimized**: Built for NVIDIA GPUs with broad model support.
- **Seamless Integration**: Implements standard `origami-stateless` interfaces.

## Prerequisites

- **NVIDIA GPU**: Required for vLLM operations.
- **CUDA Toolkit**: Correct versions must be installed for compilation.
- **Linux OS**: Strictly Ubuntu/Debian or similar.

## Installation

This package is conditionally installed via `uv` based on the system platform:

```bash
# On a Linux machine
uv sync --extra origami-vllm
```

## Usage

```python
from origami_vllm.main import VllmRouter
from origami_stateless.models import CompletionRequest

router = VllmRouter(config)
response = await router.complete(CompletionRequest(prompt="Hello vLLM!"))
```
