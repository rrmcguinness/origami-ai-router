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

import os
import pytest
from origami_ops_sec.models import OpsSecRules, ThreatResult, AttackVectorDefinition


def test_load_ops_sec_rules_from_toml():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    toml_path = os.path.join(root_dir, "rules_ops_sec.toml")

    assert os.path.exists(toml_path), f"rules_ops_sec.toml file should exist at {toml_path}"

    rules = OpsSecRules.from_toml_file(toml_path)

    assert rules.config.threshold == 0.65
    assert rules.config.default_action == "slim"
    assert len(rules.attack_vectors) >= 5

    vector_names = [v.name for v in rules.attack_vectors]
    assert "prompt_injection" in vector_names
    assert "system_prompt_exfiltration" in vector_names
    assert "command_code_injection" in vector_names


def test_threat_result_model():
    res = ThreatResult(
        is_threat=True,
        matched_attack="prompt_injection",
        category="direct_injection",
        severity="CRITICAL",
        confidence=0.89,
        sanitized_prompt="[NEUTRALIZED]",
        raw_prompt="Ignore instructions",
    )

    assert res.is_threat is True
    assert res.matched_attack == "prompt_injection"
    assert res.confidence == 0.89
    assert res.sanitized_prompt == "[NEUTRALIZED]"
