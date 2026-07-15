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
import asyncio
from typing import Optional, Any, Callable
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from .analyzer import OpsSecAnalyzer
from .models import ThreatResult

logger = logging.getLogger(__name__)


def extract_user_prompt(callback_context: CallbackContext, llm_request: LlmRequest) -> str:
    """
    Extracts user prompt and external tool/RAG return text from context or LLM request contents
    to protect against both direct and indirect prompt injection attacks.
    """
    texts = []

    # 1. Try user_content on callback context first
    if callback_context and getattr(callback_context, "user_content", None):
        uc = callback_context.user_content
        if isinstance(uc, str) and uc.strip():
            texts.append(uc)
        elif hasattr(uc, "parts") and uc.parts:
            text_parts = [getattr(p, "text", "") for p in uc.parts if getattr(p, "text", None)]
            if text_parts:
                texts.append("".join(text_parts))

    # 2. Scan llm_request contents for user and function/tool response text parts
    if llm_request and getattr(llm_request, "contents", None):
        for content in llm_request.contents:
            role = getattr(content, "role", None)
            if role in ["user", "tool", "function"] and getattr(content, "parts", None):
                for part in content.parts:
                    t = getattr(part, "text", None)
                    if t and t not in texts:
                        texts.append(t)

    return "\n".join(texts)


def apply_slim_to_request(llm_request: LlmRequest, sanitized_text: str) -> None:
    """
    Replaces user content text parts in llm_request with sanitized_text to slim the context.
    """
    if not llm_request or not getattr(llm_request, "contents", None):
        return

    for content in llm_request.contents:
        if getattr(content, "role", None) in ["user", "tool", "function"] and getattr(content, "parts", None):
            for i, part in enumerate(content.parts):
                if getattr(part, "text", None) is not None:
                    content.parts[i] = types.Part(text=sanitized_text)


class OpsSecCallbackHandler:
    """
    Provides ADK before_model_callback implementation for operational security,
    storing threat telemetry into state and slimming/blocking poisoned prompt contexts.
    """

    def __init__(self, analyzer: OpsSecAnalyzer, action_override: Optional[str] = None) -> None:
        self.analyzer = analyzer
        self.action = action_override or analyzer.rules.config.default_action

    async def before_model_callback(
        self, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> Optional[LlmResponse]:
        """
        Callback hooked into ADK before_model_callback lifecycle stage.
        Analyzes direct user prompts and indirect RAG/tool payload inputs,
        writes threat telemetry to state, and slims/blocks execution if a threat is detected.
        """
        user_prompt = extract_user_prompt(callback_context, llm_request)
        if not user_prompt:
            return None

        threat: ThreatResult = await self.analyzer.analyze_prompt(user_prompt)

        if callback_context and hasattr(callback_context, "state"):
            callback_context.state["ops_sec_threat"] = threat.model_dump()

        if threat.is_threat:
            logger.warning(
                "OpsSec threat detected! Attack: %s | Confidence: %.4f | Action: %s",
                threat.matched_attack,
                threat.confidence,
                self.action,
            )

            if callback_context and hasattr(callback_context, "state"):
                callback_context.state["ops_sec_raw_prompt"] = threat.raw_prompt

            if self.action == "block":
                fallback_msg = self.analyzer.rules.config.fallback_response
                return LlmResponse(
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text=fallback_msg)],
                    )
                )
            elif self.action == "slim":
                apply_slim_to_request(llm_request, threat.sanitized_prompt or "")
                return None
            elif self.action == "log_only":
                return None

        return None
