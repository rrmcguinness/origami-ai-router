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
from typing import Dict

import logging

logger = logging.getLogger(__name__)

class TomlClass:
    def __init__(self, d: Dict[str, any] = None):
        if d is not None:
            for k, v in d.items():
                logger.debug("creating value for property: %s", k)
                setattr(self, k, v)
                
    def updateValues(self, d: Dict[str, any] = None):
        if d is not None:
            for k, v in d.items():
                logger.debug("overriding value for property: %s", k)
                setattr(self, k, v)