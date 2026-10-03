from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


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


def _coerce(name: str, spec: dict[str, Any], value: Any) -> Any:
    """Validate (and gently coerce) one argument against its JSON-schema fragment."""
    kind = spec.get("type")
    if kind == "integer":
        if isinstance(value, bool):
            raise ValueError(f"Argument '{name}' must be an integer")
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        elif isinstance(value, str) and value.strip().lstrip("-").isdigit():
            value = int(value.strip())
        if not isinstance(value, int):
            raise ValueError(f"Argument '{name}' must be an integer")
        if "minimum" in spec and value < spec["minimum"]:
            raise ValueError(f"Argument '{name}' must be between {spec.get('minimum')} and {spec.get('maximum')}")
        if "maximum" in spec and value > spec["maximum"]:
            raise ValueError(f"Argument '{name}' must be between {spec.get('minimum')} and {spec.get('maximum')}")
        return value
    if kind == "string":
        if not isinstance(value, str):
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                value = str(value)
            else:
                raise ValueError(f"Argument '{name}' must be a string")
        if len(value) > spec.get("maxLength", 500):
            raise ValueError(f"Argument '{name}' is too long")
        return value
    if kind == "array":
        if not isinstance(value, list):
            raise ValueError(f"Argument '{name}' must be a list")
        item_spec = spec.get("items", {})
        if len(value) > spec.get("maxItems", 10):
            raise ValueError(f"Argument '{name}' has too many items")
        return [_coerce(name, item_spec, item) for item in value]
    return value


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

    def execute(self, name: str, raw_arguments: str | dict[str, Any] | None, context: dict[str, Any]) -> dict[str, Any]:
        tool = self.get(name)
        if tool is None:
            raise ValueError("Unknown sales tool")
        if raw_arguments is None or raw_arguments == "":
            raw_arguments = "{}"
        try:
            arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
        except json.JSONDecodeError as exc:
            raise ValueError("Tool arguments must be valid JSON") from exc
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be an object")
        properties = tool.parameters.get("properties", {})
        if set(arguments) - set(properties):
            raise ValueError("Tool arguments contain unsupported fields")
        for required in tool.parameters.get("required", []):
            if required not in arguments:
                raise ValueError(f"Missing required argument: {required}")
        arguments = {key: _coerce(key, properties[key], value) for key, value in arguments.items()}
        return tool.handler(context=context, **arguments)

    def execute_safely(
        self, name: str, raw_arguments: str | dict[str, Any] | None, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Run a tool and always return a JSON-serialisable dict for the model.

        Errors are reported back to the model (so it can self-correct or explain
        them to the customer) instead of aborting the whole chat turn.
        """
        try:
            result = self.execute(name, raw_arguments, context)
            return {"ok": True, "result": result}
        except (ValueError, LookupError) as exc:
            return {"ok": False, "error": str(exc)}
        except Exception:  # noqa: BLE001 - never leak internals to the model/customer
            logger.exception("Sales tool %s failed unexpectedly", name)
            return {"ok": False, "error": "The action could not be completed right now."}
