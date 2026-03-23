
import time
from pathlib import Path
from llama_cpp import Llama
import logging

# Disable logging for cleaner output
logging.basicConfig(level=logging.ERROR)

model_path = "packages/vllm_router/src/vllm_router/gemma-3-270m-it-qat-Q4_0.gguf"

print(f"Loading model: {model_path}...")
try:
    llm = Llama(model_path=model_path, n_ctx=4096, n_threads=1, n_gpu_layers=0) # CPU only to be safe
    print("Model loaded successfully.")
    
    prompt = "Q: Where is my package #88219? A:"
    print(f"Running 5 test requests...")
    
    start_time = time.time()
    for i in range(5):
        output = llm(prompt, max_tokens=10)
        print(f"  Request {i+1} complete.")
    end_time = time.time()
    
    duration = end_time - start_time
    rps = 5 / duration
    print(f"\nSimple Performance Result:")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Throughput: {rps:.2f} RPS")

except Exception as e:
    print(f"Error: {e}")
