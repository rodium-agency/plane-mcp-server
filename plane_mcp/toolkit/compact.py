"""Response compaction: what a tool result costs the model that reads it.

Every byte a tool returns is a token the calling agent pays for, on every call.
Three things inflated Plane responses without telling the caller anything:

- FastMCP sends a dict result twice, once as JSON text and once as
  `structuredContent`. Clients that forward both to the model pay double.
- The SDK models declare every field, so a record fetched with
  `fields=id,state` still came back with twenty-odd keys set to null.
- `description_binary` is the editor's internal document state, base64 encoded.
  No agent can read it, and it is usually the largest field in the record.

`compact` removes the last two; `CompactResults` (in `plane_mcp.middleware`)
applies it to every tool result and returns it once, as compact JSON text.

A null the caller asked for by name is kept: `fields=parent` on a work item with
no parent must answer `"parent": null`, not leave the caller wondering whether
the field exists.
"""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

# Fields no tool returns, whatever the caller asked for.
NEVER_RETURNED = frozenset({"description_binary"})


def requested_fields(fields: Any) -> frozenset[str]:
    """The field names a `fields` argument asked for by name."""
    if not isinstance(fields, str):
        return frozenset()
    return frozenset(name.strip() for name in fields.split(",")) - {"", "*"}


def compact(value: Any, keep: Collection[str] = frozenset()) -> Any:
    """`value` without null-valued keys (except those in `keep`) and never-returned fields.

    Applied recursively, so it reaches the records inside a pagination envelope.
    Items of a list are never dropped, null or not: a list's length and order
    are information.
    """
    if isinstance(value, dict):
        return {
            key: compact(item, keep)
            for key, item in value.items()
            if key not in NEVER_RETURNED and (item is not None or key in keep)
        }
    if isinstance(value, list):
        return [compact(item, keep) for item in value]
    return value
