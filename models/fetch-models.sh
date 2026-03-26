#!/usr/bin/env bash

# EdgeRouter: Local Quantized Model Downloader
# Fetches the optimal Q4_K_M GGUF weights used by the llama-cpp-python engines

# Change to the directory of this script so downloads go directly into /models
cd "$(dirname "$0")" || exit 1

echo "======================================================="
echo "⚡ EdgeRouter Local Edge Fallback Provisioning ⚡"
echo "======================================================="
echo "Targeting optimal Q4_K_M quantized weights for latency."
echo "Note: These files total roughly 20GB. Grab some coffee."
echo ""

# Helper to download specific models
download_model() {
    local url=$1
    local filename=$2

    if [ -f "$filename" ]; then
        echo "[SKIP] Model '$filename' already exists. Skipping download."
    else
        echo "⬇️ Downloading: $filename"
        # Using curl with -L (follow redirects), -C - (resume if interrupted), -o (output filename)
        curl -L -C - -o "$filename" "$url"
        
        if [ $? -eq 0 ]; then
            echo "[SUCCESS] Saved $filename"
        else
            echo "[ERROR] Failed to download $filename"
        fi
    fi
}

echo "--- 1. Fetching Llama 3.1 8B Instruct ---"
download_model \
    "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf" \
    "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
echo ""

echo "--- 2. Fetching Gemma 3 12B Instruct ---"
download_model \
    "https://huggingface.co/bartowski/gemma-3-12b-it-GGUF/resolve/main/gemma-3-12b-it-Q4_K_M.gguf" \
    "gemma-3-12b-it-q4_k_m.gguf"
echo ""

echo "--- 3. Fetching Mistral NeMo 12B Instruct ---"
download_model \
    "https://huggingface.co/bartowski/Mistral-Nemo-Instruct-2407-GGUF/resolve/main/Mistral-Nemo-Instruct-2407-Q4_K_M.gguf" \
    "Mistral-Nemo-Instruct-2407-Q4_K_M.gguf"
echo ""

echo "--- 4. Fetching BAAI/bge-m3 (Sentence Transformers) ---"
if [ -d "bge-m3" ]; then
    echo "[SKIP] Model directory 'bge-m3' already exists. Skipping download."
else
    echo "⬇️ Downloading BAAI/bge-m3 via huggingface-cli..."
    # uv will find the project root and run the CLI from our virtual environment
    uv run huggingface-cli download BAAI/bge-m3 --local-dir bge-m3
    
    if [ $? -eq 0 ]; then
        echo "[SUCCESS] Saved BAAI/bge-m3 to models/bge-m3/"
    else
        echo "[ERROR] Failed to download BAAI/bge-m3"
    fi
fi
echo ""

echo "======================================================="
echo "✅ EdgeRouter Model Provisioning Complete!"
echo "Make sure your '.env.toml' paths point to these newly downloaded .gguf files."
echo "======================================================="
