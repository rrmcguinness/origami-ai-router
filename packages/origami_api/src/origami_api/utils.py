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

def deep_merge(dict1, dict2):
    """
    Recursively merges dict2 into dict1.
    Values in dict2 will override values in dict1.
    """
    for key, value in dict2.items():
        if isinstance(value, dict) and key in dict1:
            if isinstance(dict1[key], dict):
                deep_merge(dict1[key], value)
            elif hasattr(dict1[key], "__dict__"):
                # If dict1[key] is an object (like BaseConfig), convert it to dict, merge, and re-assign
                merged = deep_merge(dict1[key].__dict__, value)
                dict1[key] = type(dict1[key])(merged)
            else:
                dict1[key] = value
        else:
            dict1[key] = value
    return dict1