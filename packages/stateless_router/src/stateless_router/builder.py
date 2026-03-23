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

from typing import Type, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from .interface import StatelessRouter
from .models import RoutingRules

class RouterBuilder:
    """
    A builder for constructing StatelessRouter instances.
    Enables swapping between providers (Gemma, Gemini) while keeping 
    the rule-set consistent.
    """
    def __init__(self):
        self._router_class: Optional[Type[StatelessRouter]] = None
        self._rules: Optional[RoutingRules] = None
        self._executor: Optional[ThreadPoolExecutor] = None
        self._config: dict[str, Any] = {}

    def with_provider(self, router_cls: Type[StatelessRouter], **kwargs: Any) -> 'RouterBuilder':
        """
        Sets the implementation class for the router.
        Pass provider-specific arguments (e.g., model_path, api_key) via kwargs.
        """
        self._router_class = router_cls
        self._config.update(kwargs)
        return self

    def with_rules(self, rules: RoutingRules) -> 'RouterBuilder':
        """
        Sets the routing intent and rules for the instance.
        """
        self._rules = rules
        return self

    def with_executor(self, executor: ThreadPoolExecutor) -> 'RouterBuilder':
        """
        Sets a shared thread pool executor for async operations.
        """
        self._executor = executor
        return self

    def build(self) -> StatelessRouter:
        """
        Constructs and returns the configured StatelessRouter.
        """
        if self._router_class is None:
            raise ValueError("Darling, you forgot to provide a router implementation.")
        if self._rules is None:
            raise ValueError("You can't route without rules. Provide a RoutingRules object.")
        
        return self._router_class(rules=self._rules, executor=self._executor, **self._config)
