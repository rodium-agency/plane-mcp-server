"""Response compaction (PLANE-19)."""

from __future__ import annotations

import pytest

from plane_mcp.toolkit.compact import compact, requested_fields
from plane_mcp.toolkit.transforms import without_empty_defaults


def test_null_fields_are_dropped():
    assert compact({"id": "a", "name": None, "parent": None}) == {"id": "a"}


def test_falsy_values_that_are_not_null_are_kept():
    """An empty list of assignees, a zero and a false flag all say something."""
    record = {"assignees": [], "point": 0, "is_draft": False, "name": ""}

    assert compact(record) == record


def test_description_binary_is_never_returned():
    assert compact({"id": "a", "description_binary": "AAAA"}, keep={"description_binary"}) == {"id": "a"}


def test_a_null_the_caller_named_is_kept():
    """`fields=parent` on a work item with no parent must say so."""
    assert compact({"id": "a", "parent": None, "state": None}, keep={"parent"}) == {"id": "a", "parent": None}


def test_records_inside_an_envelope_are_compacted():
    page = {"results": [{"id": "a", "name": None, "description_binary": "x"}], "next_cursor": None, "count": 1}

    assert compact(page) == {"results": [{"id": "a"}], "count": 1}


def test_list_items_are_never_dropped():
    assert compact([None, {"a": None}, 1]) == [None, {}, 1]


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ("id, state ,", {"id", "state"}),
        ("*", set()),
        ("", set()),
        (None, set()),
        (["id"], set()),
    ],
)
def test_requested_fields(fields, expected):
    assert requested_fields(fields) == expected


def test_empty_defaults_are_stripped_and_real_ones_kept():
    schema = {
        "properties": {
            "action": {"enum": ["list"], "type": "string"},
            "name": {"default": "", "type": "string"},
            "per_page": {"default": 0, "type": "integer"},
            "is_draft": {"default": None},
            "flag": {"default": False, "type": "boolean"},
            "on": {"default": True, "type": "boolean"},
            "ids": {"default": [], "type": "array"},
            "size": {"default": 50, "type": "integer"},
            "format": {"default": "html", "type": "string"},
        },
        "required": ["action"],
    }

    stripped = without_empty_defaults(schema)["properties"]

    assert {name for name, prop in stripped.items() if "default" in prop} == {"on", "size", "format"}
    assert stripped["name"] == {"type": "string"}
    # The input schema is left alone: execution validates against it.
    assert schema["properties"]["name"]["default"] == ""
