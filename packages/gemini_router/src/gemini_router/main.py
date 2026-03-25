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
import asyncio
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from google import genai
from edgerouter_api.interfaces import StatelessRouter
from edgerouter_api.models import RoutingRules
from edgerouter_api.config import Config
from common.otel import get_tracer
import os

class GeminiRouter(StatelessRouter):
    """
    Vertex AI Gemini implementation of the StatelessRouter interface.
    Uses google-genai and Vertex AI for enterprise-grade routing.
    Configuration is pulled from common.Config.
    """
    def __init__(self, 
                 rules: RoutingRules, 
                 config: Config,
                 executor: Optional[ThreadPoolExecutor] = None,
                 **kwargs):
        super().__init__(rules=rules, config=config, executor=executor, **kwargs)
        
        router_model = config.ai_models.get_model("router")
        self.model_name = router_model.model_name if router_model else "gemini-3.1-flash-lite-preview"
        
        project_id = config.application.google_project_id or config.application.projectId
        api_key = router_model.api_key if router_model else os.environ.get("GOOGLE_API_KEY")
        
        if not project_id and not api_key:
             raise ValueError("project_id or api_key must be configured for GeminiRouter.")
        
        if api_key:
            self.client = genai.Client(
                api_key=api_key,
                vertexai=False
            )
        else:
            self.client = genai.Client(
                project=project_id,
                location=config.application.location,
                vertexai=True
            )
        
        self.system_prompt = rules.to_system_prompt()
        self.tracer = get_tracer("gemini_router")
        self.environment = os.environ.get("RUNTIME_ENV", "local")
        
        self.generation_config = {
            "system_instruction": self.system_prompt,
            "response_mime_type": "application/json",
            "temperature": router_model.temperature if router_model else 1.0,
        }
        
        thinking_config = getattr(config, "thinking_config", None)
        if thinking_config:
            self.generation_config["thinking_config"] = thinking_config

    async def route(self, user_query: str, context_summary: Optional[str] = None) -> str:
        """
        Processes the query through Gemini with strict JSON response configuration.
        Utilizes the shared executor to prevent blocking the async event loop.
        """
        loop = asyncio.get_running_loop()
        
        def _call_gemini():
            prompt = f"User prompt: {user_query}\nRoute:"
            if context_summary:
                prompt = f"Reference Context: {context_summary}\n{prompt}"
                
            return self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=self.generation_config
            )

        with self.tracer.start_as_current_span("gemini_router.route") as span:
            span.set_attribute("router.query", user_query)
            span.set_attribute("router.environment", self.environment)
            
            # Execute the blocking call in the shared thread pool
            response = await loop.run_in_executor(self.executor, _call_gemini)
            
            # Extract token usage metadata from Gemini response
            if response.usage_metadata:
                span.set_attribute("router.input_tokens", response.usage_metadata.prompt_token_count)
                span.set_attribute("router.output_tokens", response.usage_metadata.candidates_token_count)
            
            try:
                data = json.loads(response.text)
                outcome = str(data.get("route", "fallback"))
                span.set_attribute("router.outcome", outcome)
                return outcome
            except (json.JSONDecodeError, KeyError, TypeError):
                span.set_attribute("router.outcome", "fallback")
                return "fallback"