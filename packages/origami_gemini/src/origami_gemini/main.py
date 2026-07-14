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
import time
import asyncio
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from google import genai
from origami_api.interfaces import StatelessRouter
from origami_api.models import RoutingRules
from origami_api.config import Config
from origami_common.otel import get_tracer
import os

class GeminiRouter(StatelessRouter):
    """
    Vertex AI Gemini implementation of the StatelessRouter interface.
    Uses google-genai and Vertex AI for enterprise-grade routing.
    Configuration is pulled from origami_common.Config.
    """
    def __init__(self, 
                 rules: RoutingRules, 
                 config: Config,
                 executor: Optional[ThreadPoolExecutor] = None,
                 **kwargs):
        super().__init__(rules=rules, config=config, executor=executor, **kwargs)
        
        router_model = config.ai_models.get_model("router")
        self.model_name = router_model.model_name if router_model and router_model.model_name else "gemini-3.5-flash"
        
        raw_api_key = router_model.api_key if router_model else None
        api_key = raw_api_key if raw_api_key and raw_api_key != "[ENCRYPTION_KEY]" else os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        
        if api_key:
            self.client = genai.Client(
                api_key=api_key,
                vertexai=False
            )
        else:
            project_id = (
                getattr(config.application, "google_project_id", "") or 
                getattr(config.application, "projectId", "") or 
                os.environ.get("GOOGLE_CLOUD_PROJECT") or 
                os.environ.get("GCP_PROJECT") or 
                os.environ.get("GCLOUD_PROJECT") or 
                os.environ.get("GOOGLE_PROJECT")
            )
            
            if not project_id:
                try:
                    import google.auth
                    _, project_id = google.auth.default()
                except Exception:
                    pass

            if not project_id:
                raise ValueError("project_id or api_key must be configured for GeminiRouter.")
                
            location = getattr(config.application, "location", None) or "global"
            if location == "us-central1":
                location = "global"

            # Map AI Studio specific model name to Vertex AI model name
            if self.model_name == "gemini-3.1-flash-lite-preview":
                self.model_name = "gemini-3.5-flash"

            self.client = genai.Client(
                project=project_id,
                location=location,
                vertexai=True
            )
        
        base_prompt = rules.to_system_prompt()
        # Enforce highly-compressed JSON-embedded Chain of Thought reasoning for Gemini (slashing latency and preserving Llama's TTFR)
        cot_instruction = (
            'Respond ONLY with valid JSON. Use ultra-brief shorthand for reasoning.\n'
            '{ "reasoning": "kwd:brakes->auto->dumpster_fire_handler", "route": "AgentName" }'
        )
        self.system_prompt = base_prompt.replace(rules.output_schema_instruction, cot_instruction)
        self.tracer = get_tracer("origami_gemini")
        self.environment = os.environ.get("RUNTIME_ENV", None)
        
        self.generation_config = {
            "system_instruction": self.system_prompt,
            "response_mime_type": "application/json",
            "temperature": router_model.temperature if router_model else 1.0,
            "max_output_tokens": 100,
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

        with self.tracer.start_as_current_span("origami_gemini.route") as span:
            span.set_attribute("router.query", user_query)
            span.set_attribute("router.environment", self.environment)
            span.set_attribute("router.model_name", self.model_name)
            
            start_time = time.time()
            # Execute the blocking call in the shared thread pool
            response = await loop.run_in_executor(self.executor, _call_gemini)
            
            latency = time.time() - start_time
            span.set_attribute("router.latency", latency)
            
            # Extract token usage metadata from Gemini response
            if response.usage_metadata:
                span.set_attribute("router.input_tokens", response.usage_metadata.prompt_token_count)
                span.set_attribute("router.output_tokens", response.usage_metadata.candidates_token_count)
            
            try:
                data = json.loads(response.text)
                outcome = str(data.get("route", "fallback"))
                span.set_attribute("router.outcome", outcome)
                return outcome
            except Exception as e:
                span.record_exception(e)
                span.set_attribute("router.outcome", "fallback")
                return "fallback"