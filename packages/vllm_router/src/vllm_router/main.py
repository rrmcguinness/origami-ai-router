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
import asyncio
import logging
import uuid
import os

from opentelemetry import context
from edgerouter_api.interfaces import StatelessRouter
from edgerouter_api.models import RoutingRules
from edgerouter_api.config import RouterConfig
from edgerouter_api.config import Config
from common.otel import get_tracer

class VllmRouterConfig(RouterConfig):
    model_path: str

import vllm
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine
from vllm.sampling_params import SamplingParams
from vllm.sampling_params import StructuredOutputsParams

logger = logging.getLogger(__name__)

from concurrent.futures import ThreadPoolExecutor

class VllmRouter(StatelessRouter):
    """
    VllmRouter implementation of the StatelessRouter interface.
    Uses vLLM AsyncLLMEngine for high throughput continuous batching.
    """
    def __init__(self, 
                 rules: RoutingRules, 
                 config: VllmRouterConfig,
                 executor: Optional[ThreadPoolExecutor] = None,
                 **kwargs):
        super().__init__(rules=rules, config=config, executor=executor, **kwargs)
        
        model_path = config.model_path
        
        # Initialize vLLM Async Engine natively optimized for continuous request batching
        engine_args = AsyncEngineArgs(
            model=str(model_path),
            max_model_len=4096,
            gpu_memory_utilization=0.6, # Keep it conservative so we don't swap to system RAM
            enforce_eager=False
        )
        self.engine = AsyncLLMEngine.from_engine_args(engine_args)
        
        agent_names = [a.name for a in rules.agents]
        if "fallback" not in agent_names:
            agent_names.append("fallback")
            
        # vLLM utilizes outlines under the hood for guided JSON/Regex structural forcing
        choices_str = "|".join(agent_names)
        self.regex_pattern = r'\{\s*"route"\s*:\s*"(' + choices_str + r')"\s*\}'
        
        self.sampling_params = SamplingParams(
            temperature=0.0,
            max_tokens=64
        )
        # Apply structured outputs configuration dynamically due to varying kwarg support
        if hasattr(self.sampling_params, "guided_decoding"):
            self.sampling_params.guided_decoding = StructuredOutputsParams(regex=self.regex_pattern)
        else:
            # Modern API assigns it to structured_outputs
            self.sampling_params.structured_outputs = StructuredOutputsParams(regex=self.regex_pattern)
        
        self.system_prompt = rules.to_system_prompt()
        self.tracer = get_tracer("vllm_router")
        self.environment = os.environ.get("RUNTIME_ENV", "local")
        
        logger.info(f"VllmRouter initialized with vLLM engine backing model: {model_path}")

    async def route(self, user_query: str, context_summary: Optional[str] = None) -> str:
        """
        Routes the user query using asynchronous vLLM continuous batching block.
        """
        with self.tracer.start_as_current_span("vllm_router.route_vllm") as span:
            span.set_attribute("router.query", user_query)
            request_id = str(uuid.uuid4())
            span.set_attribute("router.vllm_request_id", request_id)
            
            # Gemma chat format
            user_input = f"User: {user_query}"
            if context_summary:
                user_input = f"Reference Context: {context_summary}\n{user_input}"
                
            formatted_prompt = f"<bos><start_of_turn>system\n{self.system_prompt}<end_of_turn>\n<start_of_turn>user\n{user_input}\nRoute:<end_of_turn>\n<start_of_turn>model\n"
            
            try:
                results_generator = self.engine.generate(
                    formatted_prompt, 
                    self.sampling_params, 
                    request_id
                )
                
                final_output = None
                async for request_output in results_generator:
                    final_output = request_output
                
                text = final_output.outputs[0].text
                
                # Tracing metrics
                if hasattr(final_output, "prompt_token_ids"):
                    span.set_attribute("router.input_tokens", len(final_output.prompt_token_ids))
                if hasattr(final_output.outputs[0], "token_ids"):
                    span.set_attribute("router.output_tokens", len(final_output.outputs[0].token_ids))
                
                try:
                    data = json.loads(text)
                    return str(data.get("route", "fallback"))
                except (json.JSONDecodeError, KeyError, TypeError):
                    import re
                    match = re.search(r'"route"\s*:\s*"([^"]+)"', text)
                    if match:
                        return match.group(1)
                    return "fallback"
            except Exception as e:
                span.record_exception(e)
                return "fallback"

def get_current_file_path(filename: str) -> Path:
    current_dir: Final[Path] = Path(__file__).parent.resolve()
    target_path: Final[Path] = current_dir / filename
    if not target_path.is_file():
        raise FileNotFoundError(f"'{filename}' isn't in {current_dir}.")
    return target_path