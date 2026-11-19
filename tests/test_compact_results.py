"""What a tool call costs the agent reading it, through the real server stack (PLANE-19).

Driven through `get_stdio_mcp()` and an in-memory FastMCP client, so the
middleware order, the transforms and FastMCP's own result conversion are the
ones production runs.
"""

from __future__ import annotations

import asyncio
import json
import os

import pytest
from plane.models.work_items import WorkItem

os.environ.setdefault("PLANE_API_KEY", "test")
os.environ.setdefault("PLANE_WORKSPACE_SLUG", "test")

import plane_mcp.tools.workitem as workitem_module  # noqa: E402
from plane_mcp.server import get_stdio_mcp  # noqa: E402

RECORD = WorkItem(
    id="a1",
    name="Fix login",
    state="s1",
    assignees=["u1"],
    labels=[],
    description_html="<p>long</p>",
    description_binary="QUJDREVGRw==",
)


class _Page:
    results = [RECORD]
    total_count = 1
    count = 1
    next_cursor = None
    prev_cursor = None
    next_page_results = False
    prev_page_results = False


class _WorkItems:
    def retrieve(self, **_):
        return RECORD

    def list(self, **_):
        return _Page()

    def delete(self, **_):
        return None


class _Client:
    work_items = _WorkItems()


@pytest.fixture
def call(monkeypatch):
    monkeypatch.setattr(workitem_module, "get_plane_client_context", lambda: (_Client(), "acme"))
    from fastmcp import Client

    async def run(arguments, tool="workitem"):
        async with Client(get_stdio_mcp()) as client:
            return await client.call_tool_mcp(tool, arguments)

    return lambda arguments, tool="workitem": asyncio.run(run(arguments, tool))


def _payload(result):
    (block,) = result.content
    return json.loads(block.text)


def test_a_result_is_sent_once(call):
    """Text only: the structured duplicate doubled every response."""
    result = call({"action": "retrieve", "project_id": "p", "workitem_id": "a1"})

    assert result.structuredContent is None
    assert len(result.content) == 1


def test_nulls_and_binary_are_gone(call):
    payload = _payload(call({"action": "retrieve", "project_id": "p", "workitem_id": "a1"}))

    assert payload == {
        "id": "a1",
        "name": "Fix login",
        "state": "s1",
        "assignees": ["u1"],
        "labels": [],
        "description_html": "<p>long</p>",
    }


def test_a_null_field_the_caller_asked_for_is_answered(call):
    payload = _payload(call({"action": "retrieve", "project_id": "p", "workitem_id": "a1", "fields": "id,parent"}))

    assert payload["parent"] is None
    assert "created_at" not in payload


def test_the_text_is_compact_json(call):
    (block,) = call({"action": "retrieve", "project_id": "p", "workitem_id": "a1"}).content

    assert ": " not in block.text and ", " not in block.text


def test_a_page_keeps_its_envelope_and_drops_descriptions(call):
    """Even when the API ignores `fields`, the light default holds on the way out."""
    payload = _payload(call({"action": "list", "project_id": "p"}))

    assert payload["results"] == [{"id": "a1", "name": "Fix login", "state": "s1", "assignees": ["u1"], "labels": []}]
    assert payload["next_page_results"] is False
    assert payload["count"] == 1


def test_an_error_string_stays_plain_text(call):
    result = call({"action": "retrieve", "project_id": "p"})

    assert result.content[0].text.startswith("Error:")


def test_a_delete_returns_nothing(call):
    result = call({"action": "delete", "project_id": "p", "workitem_id": "a1"})

    assert result.content == []
    assert not result.isError


def test_the_listing_drops_empty_defaults():
    from fastmcp import Client

    async def listing():
        async with Client(get_stdio_mcp()) as client:
            return await client.list_tools()

    (workitem,) = [tool for tool in asyncio.run(listing()) if tool.name == "workitem"]
    properties = workitem.inputSchema["properties"]

    assert "default" not in properties["project_id"]
    assert "default" not in properties["per_page"]
    assert properties["project_id"]["type"] == "string"
