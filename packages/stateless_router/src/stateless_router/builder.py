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
