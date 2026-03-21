import json
from pathlib import Path
from typing import Final, Dict, Any, Optional
import threading
import asyncio
import anyio

from llama_cpp import Llama, LlamaGrammar
from stateless_router.interface import StatelessRouter
from stateless_router.models import RoutingRules
from common.config import Config
from common.otel import get_tracer
import os

class GemmaRouter(StatelessRouter):
    """
    Gemma-3-270m-it implementation of the StatelessRouter interface.
    Uses llama-cpp-python and GBNF grammars for efficient local routing.
    """
    def __init__(self, rules: RoutingRules, model_path: str | Path | None = None, n_threads: int = 4):
        super().__init__(rules)
        
        self.llm = Llama(
            model_path=str(model_path),
            n_ctx=2048,
            n_threads=n_threads,
            n_gpu_layers=-1, 
            chat_format="gemma",
            verbose=False,
            logits_all=False
        )
        self.grammar = LlamaGrammar.from_string(self._build_grammar(rules))
        self.system_prompt = rules.to_system_prompt()
        
        # Warmup
        self.llm.create_chat_completion(
            messages=[{"role": "system", "content": self.system_prompt}],
            max_tokens=1
        )
        self.tracer = get_tracer("gemma_router")
        self.environment = os.environ.get("RUNTIME_ENV", "local")

    def _build_grammar(self, rules: RoutingRules) -> str:
        agent_names = [a.name for a in rules.agents]
        if "Fallback" not in agent_names:
            agent_names.append("Fallback")
            
        agent_list = " | ".join([f'"{name}"' for name in agent_names])
        return f"""
        root   ::= "{{" space "\\"route\\":" space "\\"" agent "\\"" space "}}"
        agent  ::= {agent_list}
        space  ::= " "*
        """

    def route(self, user_query: str) -> str:
        """
        Routes the user query using the pre-configured grammar and KV-cached system prompt.
        """
        with self.tracer.start_as_current_span("gemma_router.route") as span:
            span.set_attribute("router.query", user_query)
            
            response: Dict[str, Any] = self.llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"User: {user_query}\nRoute:"}
                ],
                grammar=self.grammar,
                max_tokens=64,
                temperature=0.0
            )
            
            usage = response.get("usage", {})
            span.set_attribute("router.input_tokens", usage.get("prompt_tokens", 0))
            span.set_attribute("router.output_tokens", usage.get("completion_tokens", 0))
            
            try:
                content = response["choices"][0]["message"]["content"]
                data = json.loads(content)
                return str(data.get("route", "Fallback"))
            except (json.JSONDecodeError, KeyError, TypeError):
                return "Fallback"

class GemmaWorkerPool:
    """
    Pool of GemmaRouter workers for parallel inference.
    """
    def __init__(self, rules: RoutingRules, model_path: str | Path | None = None, num_workers: int = 4):
        self.rules = rules
        self.model_path = model_path
        self.num_workers = num_workers
        self.workers = asyncio.Queue()
        self.tracer = get_tracer("gemma_worker_pool")

    async def initialize(self):
        """Initializes the worker pool."""
        config = Config()
        server_cfg = getattr(config.baseConfig, "server", None)
        n_threads = getattr(server_cfg, "n_threads", 0)
        if n_threads <= 0:
            n_threads = max(1, (os.cpu_count() or 2) // self.num_workers)

        for _ in range(self.num_workers):
            worker = GemmaRouter(self.rules, self.model_path, n_threads=n_threads)
            await self.workers.put(worker)
        
        print(f"GemmaWorkerPool initialized with {self.num_workers} workers.")

    async def route_async(self, user_query: str) -> str:
        """Acquires a worker and routes the query."""
        with self.tracer.start_as_current_span("gemma_worker_pool.route_async") as span:
            worker = await self.workers.get()
            try:
                # Use anyio to run the sync route call in a thread
                return await anyio.to_thread.run_sync(worker.route, user_query)
            finally:
                await self.workers.put(worker)

def get_current_file_path(filename: str) -> Path:
    current_dir: Final[Path] = Path(__file__).parent.resolve()
    target_path: Final[Path] = current_dir / filename
    if not target_path.is_file():
        raise FileNotFoundError(f"'{filename}' isn't in {current_dir}.")
    return target_path