# Origami AI Router - Gemini Package (`origami-gemini`)

The `origami-gemini` package provides cloud-primary intent classification using Google's **Gemini 3.5 Flash** models via the official `google-genai` SDK over Vertex AI or Google AI Studio.

---

## Features

- **Gemini 3.5 Flash Primary Routing**: High-throughput, cloud-managed inference achieving 100% zero-shot classification baseline against complex multi-agent matrices.
- **Zero-Fat Chain of Thought (CoT)**: Custom JSON schema prompting requiring ultra-brief shorthand reasoning (`"reasoning": "kwd:X->auto->Y"`) before producing the target `route`.
- **Mechanical Output Capping**: Caps generation to `max_output_tokens=100` to physically mitigate latency jitter and suppress infinite generation loops.
- **Dual SDK Authentication**: Seamlessly authenticates via Google Cloud Application Default Credentials (ADC) for Vertex AI or `GEMINI_API_KEY` for Google AI Studio.

---

## Configuration

In `.env.toml` or via explicit configuration:

```toml
[ai_models.router]
model_name = "gemini-3.5-flash"
temperature = 0.0
```

---

## Usage Example

```python
import asyncio
from origami_api.config import Config
from origami_api.models import RoutingRules
from origami_gemini.main import GeminiRouter

async def main():
    config = Config()
    rules = RoutingRules.from_toml_file("rules.toml")

    # Instantiate GeminiRouter
    router = GeminiRouter(rules=rules, config=config)

    # Perform asynchronous routing call
    query = "I want to return a pair of boots I bought last week."
    target_route = await router.route(query)

    print(f"Target Route: {target_route}")

if __name__ == "__main__":
    asyncio.run(main())
```
