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

from typing import Type, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from origami_api.interfaces import StatelessRouter
from origami_api.models import RoutingRules
from origami_api.config import Config, RouterConfig

from origami_ops_sec import OpsSecRules, OpsSecAnalyzer, OpsSecCallbackHandler


class RouterBuilder:
    """
    A builder for constructing StatelessRouter instances.
    Enables swapping between providers (Gemma, Gemini) while keeping 
    the rule-set consistent.
    """
    def __init__(self) -> None:
        self._router_class: Optional[Type[StatelessRouter]] = None
        self._rules: Optional[RoutingRules] = None
        self._executor: Optional[ThreadPoolExecutor] = None
        self._config: Optional[RouterConfig] = None
        self._kwargs: dict[str, Any] = {}

    def with_provider(self, router_cls: Type[StatelessRouter], config: RouterConfig, **kwargs: Any) -> RouterBuilder:
        """
        Sets the implementation class for the router alongside its configuration object.
        Extra provider-specific overrides can be passed via kwargs.
        """
        self._router_class = router_cls
        self._config = config
        self._kwargs.update(kwargs)
        return self

    def with_rules(self, rules: RoutingRules) -> RouterBuilder:
        """
        Sets the routing intent and rules for the instance.
        """
        self._rules = rules
        return self

    def with_executor(self, executor: ThreadPoolExecutor) -> RouterBuilder:
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
        if self._config is None:
            raise ValueError("A valid RouterConfig object must be provided.")
        
        return self._router_class(rules=self._rules, config=self._config, executor=self._executor, **self._kwargs)


class OpsSecBuilder:
    """
    A builder for constructing OpsSec pre-processors and ADK before_model_callbacks.
    """
    def __init__(self) -> None:
        self._rules: Optional[OpsSecRules] = None
        self._rules_file: Optional[str] = None
        self._config: Optional[Config] = None
        self._executor: Optional[ThreadPoolExecutor] = None
        self._action_override: Optional[str] = None
        self._kwargs: dict[str, Any] = {}

    def with_rules(self, rules: OpsSecRules) -> OpsSecBuilder:
        """
        Sets explicit OpsSecRules object for the operational security pre-processor.
        """
        self._rules = rules
        return self

    def with_rules_file(self, file_path: str) -> OpsSecBuilder:
        """
        Loads rules from a TOML configuration file (e.g. rules_ops_sec.toml).
        """
        self._rules_file = file_path
        return self

    def with_config(self, config: Config) -> OpsSecBuilder:
        """
        Sets system Config instance.
        """
        self._config = config
        return self

    def with_executor(self, executor: ThreadPoolExecutor) -> OpsSecBuilder:
        """
        Sets shared ThreadPoolExecutor for background vector embeddings computation.
        """
        self._executor = executor
        return self

    def with_action(self, action: str) -> OpsSecBuilder:
        """
        Overrides default action (e.g. "slim", "block", "log_only").
        """
        self._action_override = action
        return self

    def with_kwargs(self, **kwargs: Any) -> OpsSecBuilder:
        """
        Passes additional kwargs to EmberRouter underlying model.
        """
        self._kwargs.update(kwargs)
        return self

    def build_analyzer(self) -> OpsSecAnalyzer:
        """
        Builds and returns the configured OpsSecAnalyzer.
        """
        if self._rules is None:
            if self._rules_file:
                self._rules = OpsSecRules.from_toml_file(self._rules_file)
            else:
                raise ValueError("Operational security rules must be provided via with_rules() or with_rules_file().")

        return OpsSecAnalyzer(
            rules=self._rules,
            config=self._config,
            executor=self._executor,
            **self._kwargs,
        )

    def build_callback_handler(self) -> OpsSecCallbackHandler:
        """
        Builds and returns the configured OpsSecCallbackHandler.
        """
        analyzer = self.build_analyzer()
        return OpsSecCallbackHandler(analyzer=analyzer, action_override=self._action_override)

    def build_before_model_callback(self) -> Callable[..., Any]:
        """
        Builds and returns the callable before_model_callback hook for ADK agents.
        """
        handler = self.build_callback_handler()
        return handler.before_model_callback
