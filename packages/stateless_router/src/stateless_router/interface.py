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

from abc import ABC, abstractmethod
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from .models import RoutingRules

class StatelessRouter(ABC):
    """
    Abstract Base Class for all router implementations.
    Every provider (Gemma, Gemini, etc.) will implement this interface.
    """
    def __init__(self, rules: RoutingRules, executor: Optional[ThreadPoolExecutor] = None):
        self.rules = rules
        self.executor = executor

    @abstractmethod
    async def route(self, user_query: str, context_summary: Optional[str] = None) -> str:
        """
        Processes the query and returns the target Agent name.
        """
        pass
