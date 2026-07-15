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

from __future__ import annotations

import logging
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from origami_api.models import RoutingRules, AgentDefinition
from origami_api.config import Config
from origami_ember.router import EmberRouter

from .models import OpsSecRules, ThreatResult, AttackVectorDefinition

logger = logging.getLogger(__name__)


class OpsSecAnalyzer:
    """
    Analyzes user prompts using Ember vector embeddings to determine if a prompt
    contains malicious intent or matches configured vector attack patterns.
    """

    def __init__(
        self,
        rules: OpsSecRules,
        config: Optional[Config] = None,
        executor: Optional[ThreadPoolExecutor] = None,
        **kwargs: Any,
    ) -> None:
        self.rules = rules
        self.executor = executor
        
        # Load default config if none provided
        if config is None:
            try:
                self.config = Config()
            except Exception:
                self.config = Config.__new__(Config)
        else:
            self.config = config

        self.vectors_by_name: Dict[str, AttackVectorDefinition] = {
            vector.name: vector for vector in self.rules.attack_vectors
        }

        # Convert attack vectors to RoutingRules format for EmberRouter indexing
        agents = [
            AgentDefinition(
                name=vector.name,
                description=vector.description,
                examples=vector.examples,
                salience=10,
            )
            for vector in self.rules.attack_vectors
        ]
        routing_rules = RoutingRules(agents=agents)

        logger.info("Initializing EmberRouter index for OpsSec vector attacks (%d vectors)...", len(agents))
        self.router = EmberRouter(
            rules=routing_rules,
            config=self.config,
            executor=self.executor,
            **kwargs,
        )

    async def analyze_prompt(self, user_query: str) -> ThreatResult:
        """
        Calculates similarity between incoming prompt and indexed vector attacks.
        Returns a ThreatResult indicating if the prompt exceeds the configured threat threshold.
        """
        if not self.rules.attack_vectors:
            return ThreatResult(
                is_threat=False,
                confidence=0.0,
                raw_prompt=user_query,
                sanitized_prompt=user_query,
            )

        matched_name, confidence = await self.router.route_detailed(user_query)
        threshold = self.rules.config.threshold

        if confidence >= threshold and matched_name in self.vectors_by_name:
            vector_def = self.vectors_by_name[matched_name]
            logger.warning(
                "OpsSec detected potential vector attack '%s' (category=%s, confidence=%.4f >= threshold=%.4f)",
                matched_name,
                vector_def.category,
                confidence,
                threshold,
            )
            sanitized = self.slim_prompt(user_query, matched_name)
            return ThreatResult(
                is_threat=True,
                matched_attack=matched_name,
                category=vector_def.category,
                severity=vector_def.severity,
                confidence=confidence,
                raw_prompt=user_query,
                sanitized_prompt=sanitized,
            )

        return ThreatResult(
            is_threat=False,
            confidence=confidence,
            raw_prompt=user_query,
            sanitized_prompt=user_query,
        )

    def slim_prompt(self, user_query: str, matched_attack: Optional[str] = None) -> str:
        """
        Slims/neutralizes the malicious user query context so it does not poison the model context.
        """
        attack_label = matched_attack or "VECTOR_ATTACK"
        return f"[NEUTRALIZED PROMPT VECTOR ATTACK: Intent matches '{attack_label}'. Original payload stripped.]"
