"""Base abstraction for LLM tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ToolExecutionError(RuntimeError):
    """Raised when a tool execution fails."""


class BaseTool(ABC):
    """Base interface for all tools exposed to LLM agents."""

    name: str
    description: str
    parameters_schema: dict[str, Any]

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """Execute the tool with the provided arguments from the LLM."""
        pass
