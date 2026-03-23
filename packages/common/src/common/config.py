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

'''
Copyright 2024 Google, LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

	http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

import toml

import os
from .model import BaseConfig
from .utils import deep_merge

class Config:
    baseConfig: BaseConfig

    def __init__(self, file: str = None):
        vals = {}
        # Always load .env.toml
        if os.path.exists(".env.toml"):
            with open(".env.toml", 'r') as f:
                vals = toml.load(f)

        # If a local toml file exists, load and merge it
        if os.path.exists(".env.local.toml"):
            with open(".env.local.toml", 'r') as f:
                local_vals = toml.load(f)
                vals = deep_merge(vals, local_vals)
        
        # Determine specific file to load
        specific_file = file
        if specific_file is None:
            runtime_env = os.environ.get("RUNTIME_ENV")
            if runtime_env:
                specific_file = f".env.{runtime_env}.toml"
        
        # If specific file is provided/determined, load and merge it
        if specific_file and specific_file != ".env.toml" and os.path.exists(specific_file):
            with open(specific_file, 'r') as f:
                specific_vals = toml.load(f)
            # Merge
            vals = deep_merge(vals, specific_vals)
        
        self.baseConfig = BaseConfig(vals)
