# Setting Up CUDA / GPU Support for Edge Routers

This guide walks you through the steps required to compile and run `llama-cpp-python` with CUDA (GPU offloading) enabled on this project. By default, pre-compiled GPU wheels might not exist for your specific Python version (e.g., Python 3.13), so compiling from source is recommended.

---

## Prerequisites

- An NVIDIA GPU (e.g., RTX 4090, L4, T4, A100)
- NVIDIA Drivers installed (`nvidia-smi` active)
- Linux environment (e.g., Ubuntu, KDE neon, Debian)

---

## 1. Install the CUDA Toolkit and Compiler

To compile `llama-cpp-python` with CUDA, you need the CUDA toolkit, which provides the `nvcc` compiler.

**On Ubuntu / Debian-based systems:**
```bash
sudo apt-get update
sudo apt-get install -y nvidia-cuda-toolkit
```

> [!IMPORTANT]
> Verify the installation by checking where `nvcc` is located. It is commonly found at `/usr/bin/nvcc` or in directories like `/usr/local/cuda-<version>/bin/nvcc`.

---

## 2. Compile `llama-cpp-python` with CUDA

Ensure your project uses `uv` for dependency management. Since we need to force `uv` to compile `llama-cpp-python` from source instead of using a cached CPU wheel, use specific installation flags.

Run the following command in the project root:

```bash
# Export the CUDACXX path if nvcc is not on your global PATH.
export CUDACXX=/path/to/your/nvcc

# Force uv to build from source and enable CUDA
CMAKE_ARGS="-DGGML_CUDA=on" uv pip install llama-cpp-python --reinstall --no-binary llama-cpp-python --no-cache-dir
```

> [!TIP]
> This compilation step can take several minutes as it compiles all CUDA kernels from scratch.

---

## 3. Verification

The `LlamaCppRouter` class in `origami_llama_cpp` is configured to check if GPU offload is supported at runtime. If CUDA is not correctly configured, it will log a warning that it has fallen back to the CPU.

You can proactively test your installation by running a simple python snippet:

```bash
uv run python -c "from llama_cpp import llama_supports_gpu_offload; print('GPU Offload active:', llama_supports_gpu_offload())"
```

If this prints **`GPU Offload active: True`**, your setup was successful!

You can also run the load tests to observe accelerated processing speeds:
```bash
uv run pytest tests/integration/test_llama_cpp_load.py
```
