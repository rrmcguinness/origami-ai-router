# Origami Operational Security (`origami_ops_sec`)

`origami_ops_sec` provides real-time vector attack detection and mitigation pre-processing for LLM prompts, using Ember embeddings and Google ADK callbacks.

## Key Features
- Configurable rules via `rules_ops_sec.toml` defining prompt attack vector embeddings (direct injection, exfiltration, jailbreaks, code execution).
- Uses `EmberRouter` embedding strategy to compute cosine similarity between incoming user queries and indexed vector attack definitions.
- Provides `before_model_callback` for ADK Agents to store threat telemetry state and slim/neutralize poisoned context before LLM processing.
