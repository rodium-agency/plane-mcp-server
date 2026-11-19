"""Surface-agnostic FastMCP listing transforms.

A transform here must be safe to apply to any catalogue. Anything that encodes a
specific catalogue's history -- the retired name aliases, for instance -- belongs with
that catalogue, not here.

`StripOutputSchemas` drops `outputSchema` from the advertised listing: two thirds
of the wire payload, for a field the MCP spec makes optional and defines as a
client-side validation contract. Execution is untouched, so clients that consume
`structuredContent` keep receiving it and lose validation only.

`StripEmptyDefaults` drops a parameter's `default` when it is an empty value --
`""`, `0`, `false`, `null`, `[]`. Every optional parameter of a dispatch tool
defaults to "not given", so the listing repeated `"default": ""` some two
hundred times, and the listing heads every conversation. A parameter left out
of `required` already says it may be omitted; a default that carries a real
value (`"default": 50`) is kept, since that one tells the caller something.
Execution keeps the full schema, so the server still applies every default.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastmcp.server.transforms import Transform
from fastmcp.tools.base import Tool

EMPTY_DEFAULTS: tuple[Any, ...] = ("", 0, False, None, [])


class StripOutputSchemas(Transform):
    async def list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]:
        return [tool.model_copy(update={"output_schema": None}) for tool in tools]


def without_empty_defaults(schema: dict[str, Any]) -> dict[str, Any]:
    """`schema` with every empty `default` removed from its top-level properties."""
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return schema
    trimmed = {}
    for name, prop in properties.items():
        if isinstance(prop, dict) and "default" in prop and _is_empty(prop["default"]):
            prop = {key: value for key, value in prop.items() if key != "default"}
        trimmed[name] = prop
    return {**schema, "properties": trimmed}


def _is_empty(value: Any) -> bool:
    # `type` first: 0 == False and "" != 0, but True == 1 must not be read as empty.
    return any(type(value) is type(empty) and value == empty for empty in EMPTY_DEFAULTS)


class StripEmptyDefaults(Transform):
    async def list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]:
        return [tool.model_copy(update={"parameters": without_empty_defaults(tool.parameters)}) for tool in tools]
