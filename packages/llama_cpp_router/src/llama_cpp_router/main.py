# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from pathlib import Path
from typing import Final, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import threading
import asyncio
import anyio
import logging
import os

from opentelemetry import context
from stateless_router.interface import StatelessRouter
from stateless_router.models import RoutingRules
from common.config import Config
from common.otel import get_tracer

from llama_cpp import Llama, LlamaGrammar
from llama_cpp import llama_supports_gpu_offload

logger = logging.getLogger(__name__)

class LlamaCppRouter(StatelessRouter):
    """
    Llama.cpp implementation of the StatelessRouter interface.
    Uses threaded worker pool for synchronous grammar parsing.
    """
    def __init__(self, 
                 rules: RoutingRules, 
                 executor: Optional[ThreadPoolExecutor] = None,
                 model_path: str | Path | None = None, 
                 n_threads: int = 4):
        super().__init__(rules, executor)
        if not model_path:
            model_path = get_current_file_path("gemma-3-270m-it-qat-Q4_0.gguf")
            
        logger.info(f"CUDA OFF-LOAD natively supported by llama_cpp: {llama_supports_gpu_offload()}")

        # Auto-detect chat format from model filename
        model_name_lower = str(model_path).lower()
        if "llama-3" in model_name_lower:
            chat_format = "llama-3"
        elif "gemma" in model_name_lower:
            chat_format = "gemma"
        else:
            chat_format = "gemma" # Default to gemma
            
        logger.info(f"Initialized LlamaCpp with chat_format: {chat_format} (detected from {model_path})")

        self.llm = Llama(
            model_path=str(model_path),
            n_ctx=4096,
            n_threads=n_threads,
            n_gpu_layers=-1, 
            chat_format=chat_format,
            verbose=False
        )
        self.grammar = self._build_grammar()
        self.system_prompt = rules.to_system_prompt()
        self.tracer = get_tracer("llama_cpp_router")

    def _build_grammar(self) -> LlamaGrammar:
        agent_names = [a.name for a in self.rules.agents]
        if "Fallback" not in agent_names:
            agent_names.append("Fallback")
            
        schema = {
            "type": "object",
            "properties": {
                "route": {
                    "type": "string",
                    "enum": agent_names
                }
            },
            "required": ["route"],
            "additionalProperties": False
        }
        return LlamaGrammar.from_json_schema(json.dumps(schema))

    async def route(self, user_query: str, context_summary: Optional[str] = None) -> str:
        """
        Routes the query using local Llama model.
        Execution is offloaded to the shared ThreadPoolExecutor.
        """
        loop = asyncio.get_running_loop()
        
        def _sync_route():
            with self.tracer.start_as_current_span("llama_cpp_router.route_sync") as span:
                span.set_attribute("router.query", user_query)
                
                # Explicitly list available agents for structural grounding
                router_types = ", ".join([a.name for a in self.rules.agents])
                
                # Use as system prompt (chat_format handles the model-specific template tags)
                instruction_prompt = (
                    f"Constrain all responses to the following router types: {router_types}\n\n"
                    f"{self.system_prompt}\n\n"
                    "Your response MUST be a single JSON object containing only the 'route' key. "
                    "Do not include any conversational text or explanation."
                )
                
                # Constructing the message (llama-cpp-python formats these correctly per template)
                messages = [
                    {"role": "system", "content": instruction_prompt},
                    {"role": "user", "content": f"Query: {user_query}\nRoute JSON:"}
                ]
                
                response: Dict[str, Any] = self.llm.create_chat_completion(
                    messages=messages,
                    grammar=self.grammar,
                    temperature=0.0
                )
                
                if "usage" in response:
                    span.set_attribute("router.input_tokens", response["usage"].get("prompt_tokens", 0))
                    span.set_attribute("router.output_tokens", response["usage"].get("completion_tokens", 0))
                    
                try:
                    content = response['choices'][0]['message']['content']
                    # Some versions of llama-cpp might return conversational text despite the grammar
                    # if the grammar isn't strictly enforced on the first token. 
                    # We'll parse the JSON safely.
                    data = json.loads(content)
                    return str(data.get("route", "Fallback"))
                except (KeyError, IndexError, json.JSONDecodeError) as e:
                    span.record_exception(e)
                    return "Fallback"
        
        return await loop.run_in_executor(self.executor, _sync_route)


class LlamaCppWorkerPool(StatelessRouter):
    """
    Pool of LlamaCppRouter workers for multithreaded inference.
    Participates in the shared ThreadPoolExecutor.
    """
    def __init__(self, 
                 rules: RoutingRules, 
                 executor: Optional[ThreadPoolExecutor] = None,
                 model_path: str | Path | None = None, 
                 num_workers: int = 4):
        super().__init__(rules, executor)
        self.model_path = model_path
        self.num_workers = num_workers
        self.workers: asyncio.Queue[LlamaCppRouter] = asyncio.Queue()
        self.tracer = get_tracer("llama_cpp_worker_pool")
        self.initialized = False
        
    async def initialize(self):
        if self.initialized:
            return
        logger.info(f"Initializing {self.num_workers} LlamaCpp workers...")
        for _ in range(self.num_workers):
            # Each worker gets the shared executor
            worker = LlamaCppRouter(self.rules, self.executor, self.model_path)
            await self.workers.put(worker)
        self.initialized = True
        logger.info("LlamaCpp worker pool initialization complete.")

    async def route(self, user_query: str, context_summary: Optional[str] = None) -> str:
        if not self.initialized:
            await self.initialize()
            
        with self.tracer.start_as_current_span("llama_cpp_worker_pool.route") as span:
            worker = await self.workers.get()
            try:
                # Delegate to the worker's async route method
                return await worker.route(user_query, context_summary=context_summary)
            finally:
                await self.workers.put(worker)

def get_current_file_path(filename: str) -> Path:
    current_dir: Final[Path] = Path(__file__).parent.resolve()
    target_path: Final[Path] = current_dir / filename
    if not target_path.is_file():
        raise FileNotFoundError(f"'{filename}' isn't in {current_dir}.")
    return target_path