# Origami AI Router - Gemini Router Package

The `origami-gemini` package implements the `origami-stateless` interfaces for Google's Gemini models using the `google-genai` SDK.

## Features

- **Gemini Pro/Flash Support**: Integration with latest Google Gemini models.
- **Vertex AI & Generative AI SDK**: High-level abstractions for model interaction.
- **Stateless Implementation**: Adheres to the core routing standards of the Origami AI Router project.

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
from origami_gemini.main import GeminiRouter
from origami_stateless.models import CompletionRequest

router = GeminiRouter(config)
response = await router.complete(CompletionRequest(prompt="Hello Gemini!"))
```
