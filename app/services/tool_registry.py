from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SalesTool:
    name: str
    description: str
    handler: Callable[..., Any]


class ToolRegistry:
    """Registry for safe, store-scoped sales-agent tools."""

    def __init__(self) -> None:
        self._tools: dict[str, SalesTool] = {}

    def register(self, tool: SalesTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> SalesTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[SalesTool]:
        return list(self._tools.values())
