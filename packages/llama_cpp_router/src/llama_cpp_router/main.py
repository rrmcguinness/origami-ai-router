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
from edgerouter_api.interfaces import StatelessRouter
from edgerouter_api.models import RoutingRules
from edgerouter_api.config import RouterConfig
from edgerouter_api.config import Config
from common.otel import get_tracer

class LlamaCppRouterConfig(RouterConfig):
    model_path: str
    n_threads: int = 4

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
                 config: LlamaCppRouterConfig,
                 executor: Optional[ThreadPoolExecutor] = None,
                 **kwargs):
        super().__init__(rules=rules, config=config, executor=executor, **kwargs)
        
        model_path = config.model_path
        n_threads = config.n_threads
            
        logger.info(f"CUDA OFF-LOAD natively supported by llama_cpp: {llama_supports_gpu_offload()}")

        # Auto-detect chat format from model filename
        model_name_lower = str(model_path).lower()
        if "llama-3" in model_name_lower:
            chat_format = "llama-3"
        elif "gemma" in model_name_lower:
            chat_format = "gemma"
        elif "mistral" in model_name_lower:
            chat_format = "chatml"
        else:
            chat_format = "chatml" # Default all unhandled edges to standard ChatML format
            
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
        if "fallback" not in agent_names:
            agent_names.append("fallback")
            
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
                user_content = f"Query: {user_query}\n"
                if context_summary:
                    user_content = f"Context from previous turns: {context_summary}\n" + user_content
                user_content += "Route JSON:"

                # Different chat templates behave radically different with explicit system roles.
                # Gemma and Mistral models in particular are known to scramble or ignore {"role": "system"}
                # under certain llama.cpp template alignments.
                if "gemma" in str(self.llm.model_path).lower() or "mistral" in str(self.llm.model_path).lower():
                    messages = [
                        {"role": "user", "content": f"System Instructions:\n{instruction_prompt}\n\nUser Request:\n{user_content}"}
                    ]
                else:
                    messages = [
                        {"role": "system", "content": instruction_prompt},
                        {"role": "user", "content": user_content}
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
                    return str(data.get("route", "fallback"))
                except (KeyError, IndexError, json.JSONDecodeError) as e:
                    span.record_exception(e)
                    return "fallback"
        
        return await loop.run_in_executor(self.executor, _sync_route)


class LlamaCppWorkerPool(StatelessRouter):
    """
    Pool of LlamaCppRouter workers for multithreaded inference.
    Participates in the shared ThreadPoolExecutor.
    """
    def __init__(self, 
                 rules: RoutingRules, 
                 config: LlamaCppRouterConfig,
                 executor: Optional[ThreadPoolExecutor] = None,
                 **kwargs):
        super().__init__(rules=rules, config=config, executor=executor, **kwargs)
        
        self.model_path = config.model_path
        self.num_workers = config.n_threads
        
        self.workers: asyncio.Queue[LlamaCppRouter] = asyncio.Queue()
        self.tracer = get_tracer("llama_cpp_worker_pool")
        self.initialized = False
        
    async def initialize(self):
        if self.initialized:
            return
        logger.info(f"Initializing {self.num_workers} LlamaCpp workers...")
        for _ in range(self.num_workers):
            # Each worker gets the shared executor
            worker = LlamaCppRouter(self.rules, self.config, self.executor)
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