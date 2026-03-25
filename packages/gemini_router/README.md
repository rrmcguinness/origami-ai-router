# EdgeRouter - Gemini Router Package

The `gemini-router` package implements the `stateless-router` interfaces for Google's Gemini models using the `google-genai` SDK.

## Features

- **Gemini Pro/Flash Support**: Integration with latest Google Gemini models.
- **Vertex AI & Generative AI SDK**: High-level abstractions for model interaction.
- **Stateless Implementation**: Adheres to the core routing standards of the EdgeRouter project.

## Configuration

Requires valid Google Cloud credentials and project setup.

```toml
[router.gemini]
model = "gemini-1.5-pro"
project = "my-gcp-project"
location = "us-central1"
```

## Usage

```python
from gemini_router.main import GeminiRouter
from stateless_router.models import CompletionRequest

router = GeminiRouter(config)
response = await router.complete(CompletionRequest(prompt="Hello Gemini!"))
```
