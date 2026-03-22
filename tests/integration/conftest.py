import os
import pytest

# Ensure the Config singleton always loads .env.integration.toml
os.environ["RUNTIME_ENV"] = "integration"
