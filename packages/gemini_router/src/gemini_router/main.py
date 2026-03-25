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
from stateless_router.interface import StatelessRouter
from stateless_router.models import RoutingRules
from common.config import Config
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
                 executor: Optional[ThreadPoolExecutor] = None,
                 project_id: str | None = None, 
                 location: str | None = None,
                 google_base_url: str | None = None):
        super().__init__(rules, executor)
        
        # Load from config if not provided
        config = Config()
        app_config = getattr(config.baseConfig, "application", None)
        
        project_id = project_id or getattr(app_config, "google_project_id", "rmcguinness")
        location = location or getattr(app_config, "google_location", "us-central1")
        api_key = getattr(app_config, "google_api_key", None)
        google_base_url = google_base_url or getattr(app_config, "google_base_url", None)

        http_options = None
        if google_base_url:
            from google.genai import types
            http_options = types.HttpOptions(base_url=google_base_url)

        if api_key:
            self.client = genai.Client(
                api_key=api_key,
                vertexai=False,
                http_options=http_options
            )
        else:
            self.client = genai.Client(
                project=project_id,
                location=location,
                vertexai=True,
                http_options=http_options
            )
        self.system_prompt = rules.to_system_prompt()
        self.tracer = get_tracer("gemini_router")
        self.environment = os.environ.get("RUNTIME_ENV", "local")

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
                model="gemini-3.1-flash-lite-preview",
                contents=prompt,
                config={
                    "system_instruction": self.system_prompt,
                    "response_mime_type": "application/json",
                    "temperature": 0.0
                }
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
                outcome = str(data.get("route", "Fallback"))
                span.set_attribute("router.outcome", outcome)
                return outcome
            except (json.JSONDecodeError, KeyError, TypeError):
                span.set_attribute("router.outcome", "Fallback")
                return "Fallback"