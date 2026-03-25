# EdgeRouter - Stateless Router Package

The `stateless-router` package defines the core abstractions, interfaces, and shared Pydantic models used by all specific router implementations (Gemini, vLLM, llama.cpp).

## Core Components

- **`interface.py`**: Defines the `Router` base class and standard methods for LLM interaction.
- **`models.py`**: Contains Pydantic models for request and response validation, ensuring consistency across different backends.
- **`builder.py`**: Provides a common builder pattern for initializing router instances with standard configurations.

## Architecture

This package follows a "plug-and-play" architecture. Specific router implementations inherit from the base classes defined here to provide consistent behavior regardless of the underlying inference engine.

## Usage

When implementing a new router:

```python
from stateless_router.interface import Router
from stateless_router.models import CompletionRequest

class MyNewRouter(Router):
    async def complete(self, request: CompletionRequest):
        # Implementation...
```
