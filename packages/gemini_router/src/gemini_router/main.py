import json
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
    def __init__(self, rules: RoutingRules, project_id: str | None = None, location: str | None = None):
        super().__init__(rules)
        
        # Load from config if not provided
        config = Config()
        app_config = getattr(config.baseConfig, "application", None)
        
        project_id = project_id or getattr(app_config, "google_project_id", "rmcguinness")
        location = location or getattr(app_config, "google_location", "us-central1")
        api_key = getattr(app_config, "google_api_key", None)

        if api_key:
            self.client = genai.Client(
                api_key=api_key,
                vertexai=False
            )
        else:
            self.client = genai.Client(
                project=project_id,
                location=location,
                vertexai=True
            )
        self.system_prompt = rules.to_system_prompt()
        self.tracer = get_tracer("gemini_router")
        self.environment = os.environ.get("RUNTIME_ENV", "local")

    def route(self, user_query: str) -> str:
        """
        Processes the query through Gemini with strict JSON response configuration.
        """
        with self.tracer.start_as_current_span("gemini_router.route") as span:
            span.set_attribute("router.query", user_query)
            span.set_attribute("router.environment", self.environment)
            
            response = self.client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=f"User prompt: {user_query}\nRoute:",
                config={
                    "system_instruction": self.system_prompt,
                    "response_mime_type": "application/json"
                }
            )
            
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