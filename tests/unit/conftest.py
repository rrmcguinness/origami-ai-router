import os
import pytest

# Ensure the Config singleton always loads .env.unit.toml
os.environ["RUNTIME_ENV"] = "unit"
