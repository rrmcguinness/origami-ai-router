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
from origami_stateless.builder import OpsSecBuilder
from origami_ops_sec.analyzer import OpsSecAnalyzer
from origami_ops_sec.callbacks import OpsSecCallbackHandler


def test_ops_sec_builder_with_rules_file():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    toml_path = os.path.join(root_dir, "rules_ops_sec.toml")

    builder = OpsSecBuilder().with_rules_file(toml_path).with_action("block")

    analyzer = builder.build_analyzer()
    assert isinstance(analyzer, OpsSecAnalyzer)

    handler = builder.build_callback_handler()
    assert isinstance(handler, OpsSecCallbackHandler)
    assert handler.action == "block"

    callback = builder.build_before_model_callback()
    assert callable(callback)
