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

from __future__ import annotations

import os
import toml
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AttackVectorDefinition(BaseModel):
    """
    Definition of a specific prompt vector attack category and pattern examples.
    """
    name: str
    category: str
    description: str
    severity: str = "HIGH"
    examples: List[str] = Field(default_factory=list)


class OpsSecConfig(BaseModel):
    """
    Configuration parameters for operational security filtering.
    """
    threshold: float = 0.65
    default_action: str = "slim"  # "slim", "block", "log_only"
    fallback_response: str = (
        "Security Alert: Prompt contains potential vector attack patterns and has been neutralized."
    )


class OpsSecRules(BaseModel):
    """
    Complete rule-set loaded from rules_ops_sec.toml defining configuration
    and known vector attack patterns.
    """
    config: OpsSecConfig = Field(default_factory=OpsSecConfig)
    attack_vectors: List[AttackVectorDefinition] = Field(default_factory=list)

    @classmethod
    def from_toml_file(cls, file_path: str) -> OpsSecRules:
        """
        Loads and validates an OpsSecRules instance from a TOML configuration file.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"OpsSec configuration file not found at: {file_path}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = toml.load(f)

        return cls.model_validate(data)


class ThreatResult(BaseModel):
    """
    Structure representing the evaluation output of a prompt security analysis.
    """
    is_threat: bool
    matched_attack: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    confidence: float = 0.0
    sanitized_prompt: Optional[str] = None
    raw_prompt: str = ""
