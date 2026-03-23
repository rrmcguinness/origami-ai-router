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
    async def route(self, user_query: str) -> str:
        """
        Processes the query and returns the target Agent name.
        """
        pass
