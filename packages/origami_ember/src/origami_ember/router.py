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

import os
import hashlib
import logging
import numpy as np
import torch
import asyncio
from typing import Optional, List, Dict
from concurrent.futures import ThreadPoolExecutor

from origami_api.interfaces import StatelessRouter
from origami_api.models import RoutingRules, AgentDefinition
from origami_api.config import Config, RouterConfig

logger = logging.getLogger(__name__)


def _compute_cache_key(model_name: str, keys: List[str]) -> str:
    hasher = hashlib.sha256()
    hasher.update(model_name.encode("utf-8"))
    for k in keys:
        hasher.update(k.encode("utf-8"))
    return hasher.hexdigest()


class EmberRouter(StatelessRouter):
    """
    An optimized in-memory embedding based router using sentence-transformers (BGE-M3 model).
    Implements per-example embedding strategy, binary disk tensor caching, and lazy model initialization.
    """

    def __init__(self, rules: RoutingRules, config: Config, executor: Optional[ThreadPoolExecutor] = None, **kwargs):
        router_config_data = kwargs.get("router_config", {})
        if isinstance(router_config_data, dict):
            self.ember_config = RouterConfig(**router_config_data)
        else:
            self.ember_config = router_config_data

        super().__init__(rules, config, executor, **kwargs)
        
        self.model_name = kwargs.get("model_path", "models/bge-m3")
        self.extra_kwargs = kwargs
        self._model = None
        
        if torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"
            
        self._initialize_index()

    @property
    def model(self):
        """
        Lazy-loads the SentenceTransformer model on demand.
        """
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info("Lazy-loading SentenceTransformer model '%s' on device '%s'...", self.model_name, self.device)
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def _initialize_index(self):
        """
        Generates embeddings for all agents using a per-example strategy.
        Loads pre-computed binary tensor cache if available for instant microsecond startup.
        """
        logger.info("Initializing keys for EmberRouter...")
        
        self.agent_mapping: List[str] = []
        self.keys_to_embed: List[str] = []
        
        for agent in self.rules.agents:
            primary_key = f"Agent: {agent.name}\nDescription: {agent.description}"
            if getattr(agent, 'instructions', None):
                primary_key += f"\nInstructions: {agent.instructions}"
            
            self.keys_to_embed.append(primary_key)
            self.agent_mapping.append(agent.name)
            
            if self.ember_config.enable_per_example and agent.examples:
                for example in agent.examples:
                    self.keys_to_embed.append(example)
                    self.agent_mapping.append(agent.name)
        
        if not self.keys_to_embed:
            logger.warning("No agents defined in RoutingRules for EmberRouter!")
            self.agent_embeddings = np.array([])
            return

        cache_dir = self.extra_kwargs.get("cache_dir", os.path.join(os.getcwd(), ".cache", "embeddings"))
        os.makedirs(cache_dir, exist_ok=True)
        cache_key = _compute_cache_key(self.model_name, self.keys_to_embed)
        cache_file = os.path.join(cache_dir, f"{cache_key}.npy")

        if os.path.exists(cache_file):
            logger.info("Loading pre-computed binary tensor cache from '%s'...", cache_file)
            self.agent_embeddings = np.load(cache_file)
        else:
            logger.info("Encoding %d keys into vectors via %s...", len(self.keys_to_embed), self.model_name)
            self.agent_embeddings = self.model.encode(self.keys_to_embed, convert_to_numpy=True)
            
            # Normalize agent embeddings for faster cosine similarity via dot product
            norms = np.linalg.norm(self.agent_embeddings, axis=1, keepdims=True)
            self.agent_embeddings = self.agent_embeddings / np.where(norms > 0, norms, 1.0)
            
            try:
                np.save(cache_file, self.agent_embeddings)
                logger.info("Saved pre-computed binary tensor cache to '%s'", cache_file)
            except Exception as e:
                logger.warning("Failed to save binary embedding cache: %s", e)

        logger.info("EmberRouter index initialized with %d total vectors covering %d agents.", 
                    len(self.keys_to_embed), len(self.rules.agents))

    async def route(self, user_query: str, context_summary: Optional[str] = None) -> str:
        """
        Finds the best matching agent for the given query using optimized similarity search.
        """
        best_agent, _ = await self.route_detailed(user_query, context_summary)
        return best_agent

    async def route_detailed(self, user_query: str, context_summary: Optional[str] = None) -> tuple[str, float]:
        """
        Processes the query and returns a tuple of (Agent name, confidence score).
        """
        if self.agent_embeddings.size == 0:
            logger.error("EmberRouter has no agents indexed. Routing to 'Fallback'.")
            return "Fallback", 0.0

        query_to_encode = user_query
        if self.ember_config.query_instruction:
            query_to_encode = f"{self.ember_config.query_instruction}{user_query}"
        
        if context_summary:
            query_to_encode = f"Context: {context_summary}\nQuery: {query_to_encode}"

        if self.executor:
            loop = asyncio.get_event_loop()
            query_vec = await loop.run_in_executor(
                self.executor, 
                lambda: self.model.encode([query_to_encode], convert_to_numpy=True)
            )
        else:
            query_vec = self.model.encode([query_to_encode], convert_to_numpy=True)
        
        q_vec = query_vec[0] if len(query_vec.shape) > 1 else query_vec
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = q_vec / q_norm
        
        sim_scores = np.dot(self.agent_embeddings, q_vec)
        best_match_idx = int(np.argmax(sim_scores))
        best_agent = self.agent_mapping[best_match_idx]
        confidence = float(sim_scores[best_match_idx])
        
        logger.info("EmberRouter routed query to '%s' with confidence %.4f", best_agent, confidence)
        return best_agent, confidence
