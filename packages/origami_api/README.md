# Origami AI Router - API Package (`origami-api`)

The `origami-api` package contains the core data contracts, Pydantic models, interface protocols, and hierarchical configuration parsers used across all Origami AI Router implementations.

---

## Key Modules & Classes

- **`origami_api.config`**:
  - `Config`: Hierarchical TOML configuration manager (loads `.env.toml`, `.env.test.toml`, and `.env.local.toml`).
  - `RouterConfig`: Base Pydantic model for backend router options.
- **`origami_api.models`**:
  - `RoutingRules`: Container class for agent definition matrices and system prompt synthesis (`to_system_prompt()`).
  - `AgentDefinition`: Pydantic model specifying agent `name`, `description`, `instructions`, `salience`, and `examples`.
- **`origami_api.interfaces`**:
  - `StatelessRouter`: Base abstract class defining the `async def route(user_query, context_summary)` lifecycle contract.

---

## Installation

This package is managed as part of the `uv` workspace:

```bash
uv sync --package origami-api
```

---

## Usage Example

```python
from origami_api.config import Config
from origami_api.models import RoutingRules, AgentDefinition

# 1. Initialize hierarchical configuration
config = Config()

# 2. Parse routing rules from TOML configuration
rules = RoutingRules.from_toml_file("rules.toml")

# 3. Access agent definitions sorted by salience
for agent in rules.agents:
    print(f"Agent: {agent.name} (Salience: {agent.salience})")
```
