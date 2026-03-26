# Copyright 2026 Google LLC

from abc import ABC, abstractmethod
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from .models import RoutingRules
from .config import Config

class StatelessRouter(ABC):
    """
    Abstract Base Class for all router implementations.
    Every provider (Gemma, Gemini, etc.) will implement this interface.
    """
    def __init__(self, rules: RoutingRules, config: Config, executor: Optional[ThreadPoolExecutor] = None, **kwargs):
        self.rules = rules
        self.executor = executor
        self.config = config

    @abstractmethod
    async def route(self, user_query: str, context_summary: Optional[str] = None) -> str:
        """
        Processes the query and returns the target Agent name.
        """
        pass

    async def route_detailed(self, user_query: str, context_summary: Optional[str] = None) -> tuple[str, float]:
        """
        Processes the query and returns a tuple of (Agent name, confidence score).
        Default implementation returns 1.0 confidence for models that don't support it.
        """
        outcome = await self.route(user_query, context_summary)
        return outcome, 1.0


