from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
import json


@dataclass(frozen=True)
class SalesTool:
    name: str
    description: str
    handler: Callable[..., Any]
    parameters: dict[str, Any]
    requires_confirmation: bool = False

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


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

    def execute(self, name: str, raw_arguments: str | dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        tool = self.get(name)
        if tool is None:
            raise ValueError("Unknown sales tool")
        try:
            arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
        except json.JSONDecodeError as exc:
            raise ValueError("Tool arguments must be valid JSON") from exc
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be an object")
        allowed = set(tool.parameters.get("properties", {}))
        if set(arguments) - allowed:
            raise ValueError("Tool arguments contain unsupported fields")
        return tool.handler(context=context, **arguments)
