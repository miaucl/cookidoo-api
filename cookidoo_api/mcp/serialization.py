"""Serialization helpers for Cookidoo MCP tool responses."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from importlib import import_module
from typing import Any, cast


def make_tool_result(summary: str, payload: Mapping[str, Any]) -> Any:
    """Create a ToolResult with text and structured content."""
    structured_content = cast(dict[str, Any], to_jsonable(dict(payload)))
    tool_result_cls = getattr(import_module("fastmcp.tools"), "ToolResult")
    return tool_result_cls(
        content=summary,
        structured_content=structured_content,
    )


def to_jsonable(value: Any) -> Any:
    """Convert Python objects into JSON-compatible data."""
    if is_dataclass(value) and not isinstance(value, type):
        return to_jsonable(asdict(value))

    if isinstance(value, Mapping):
        return {str(key): to_jsonable(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    return value
