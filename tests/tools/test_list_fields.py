"""Work item lists default to a light fieldset (PLANE-19).

A list is for finding work items, not reading them. Without a default every row
carried its full description, so a page of a hundred cost the agent far more
than the ids and names it was after. These pin what reaches the API, since the
API's `fields` filter is also what keeps the server from serialising the rest.
"""

from __future__ import annotations

import pytest

from plane_mcp.toolkit.paging import DEFAULT_WORKITEM_LIST_FIELDS

LISTS = [
    ("workitem", {"action": "list", "project_id": "p"}),
    ("workitem", {"action": "list"}),
    ("workitem", {"action": "list_archived", "project_id": "p"}),
    ("cycle", {"action": "list_workitems", "project_id": "p", "cycle_id": "c"}),
    ("module", {"action": "list_workitems", "project_id": "p", "module_id": "m"}),
]


def _fields_sent(spy) -> str | None:
    return spy.recorder.only().kwargs["params"].fields


@pytest.mark.parametrize(("tool", "arguments"), LISTS)
def test_a_list_without_fields_asks_only_for_the_light_default(tool, arguments, registered, spy):
    registered[tool].fn(**arguments)

    assert _fields_sent(spy) == DEFAULT_WORKITEM_LIST_FIELDS


@pytest.mark.parametrize(("tool", "arguments"), LISTS)
def test_fields_named_by_the_caller_win(tool, arguments, registered, spy):
    registered[tool].fn(**arguments, fields="id,description_html")

    assert _fields_sent(spy) == "id,description_html"


@pytest.mark.parametrize(("tool", "arguments"), LISTS)
def test_a_star_asks_for_every_field(tool, arguments, registered, spy):
    """The way back to the full record: no `fields` filter reaches the API at all."""
    registered[tool].fn(**arguments, fields="*")

    assert _fields_sent(spy) is None


def test_the_default_never_carries_a_description():
    assert "description" not in DEFAULT_WORKITEM_LIST_FIELDS


def test_retrieve_is_not_narrowed(registered, spy):
    """Reading one record is how a caller gets its description; leave it whole."""
    registered["workitem"].fn(action="retrieve", project_id="p", workitem_id="w")

    assert _fields_sent(spy) is None


@pytest.mark.parametrize("tool", ["workitem", "cycle", "module"])
def test_the_default_is_documented_where_the_caller_reads(tool, registered):
    assert DEFAULT_WORKITEM_LIST_FIELDS in registered[tool].description
    assert 'fields="*"' in registered[tool].description
