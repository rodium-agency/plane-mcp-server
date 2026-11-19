"""Exercise archive actions through the installed SDK, not a method-name spy.

PLANE-11: these exact v1 routes were missing in the self-hosted API. A successful
spy dispatch cannot establish the HTTP path, verb, cursor or error contract.
"""

from urllib.parse import parse_qs, urlparse

import pytest
import responses
from plane import PlaneClient
from plane.errors.errors import HttpError

from plane_mcp.tools import workitem

BASE = "https://plane.example.test/api/v1/workspaces/rodium/projects/project-1"


@pytest.fixture
def archive_tool(monkeypatch, registered):
    client = PlaneClient(base_url="https://plane.example.test", api_key="test-only")
    monkeypatch.setattr(workitem, "get_plane_client_context", lambda: (client, "rodium"))
    return registered["workitem"].fn


def _page(rows, *, cursor="1:1:0", more=True):
    return {
        "results": rows,
        "total_count": 2 if more else len(rows),
        "count": len(rows),
        "total_results": 2 if more else len(rows),
        "total_pages": 2 if more else 1,
        "next_cursor": cursor,
        "prev_cursor": "1:-1:1",
        "next_page_results": more,
        "prev_page_results": False,
    }


@responses.activate
def test_archived_list_keeps_cursors_and_query_fields(archive_tool):
    url = f"{BASE}/archived-work-items/"
    responses.get(url, json=_page([{"id": "archived-1", "name": "First"}]))
    result = archive_tool(
        action="list_archived",
        project_id="project-1",
        per_page=1,
        cursor="1:0:0",
        order_by="sequence_id",
        fields="id,name",
        expand="state",
    )
    assert result["results"] == [{"id": "archived-1", "name": "First"}]
    assert result["next_cursor"] == "1:1:0"
    assert result["next_page_results"] is True
    sent = responses.calls[0].request
    assert sent.headers["X-Api-Key"] == "test-only"
    assert parse_qs(urlparse(sent.url).query) == {
        "cursor": ["1:0:0"],
        "per_page": ["1"],
        "order_by": ["sequence_id"],
        "fields": ["id,name"],
        "expand": ["state"],
    }
    responses.get(url, json=_page([], more=False))
    empty = archive_tool(action="list_archived", project_id="project-1", cursor=result["next_cursor"])
    assert empty["results"] == []
    assert empty["next_page_results"] is False


@pytest.mark.parametrize(
    "archive,method,verb", [(None, responses.POST, "archive"), (False, responses.DELETE, "unarchive")]
)
@responses.activate
def test_archive_and_restore_use_sdk_routes(archive_tool, archive, method, verb):
    responses.add(method, f"{BASE}/work-items/workitem-1/{verb}/", status=204)
    result = archive_tool(action="archive", project_id="project-1", workitem_id="workitem-1", archive=archive)
    assert result == {"workitem_id": "workitem-1", "archived": archive is not False}
    assert len(responses.calls) == 1


@pytest.mark.parametrize("status", [400, 403, 404, 409])
@pytest.mark.parametrize("archive", [True, False])
@responses.activate
def test_archive_errors_never_become_success(archive_tool, status, archive):
    method, verb = (responses.POST, "archive") if archive else (responses.DELETE, "unarchive")
    responses.add(method, f"{BASE}/work-items/workitem-1/{verb}/", status=status, json={"error": "Rejected"})
    with pytest.raises(HttpError) as caught:
        archive_tool(action="archive", project_id="project-1", workitem_id="workitem-1", archive=archive)
    assert caught.value.status_code == status
    assert len(responses.calls) == 1


@responses.activate
def test_list_404_is_not_an_empty_archive(archive_tool):
    responses.get(f"{BASE}/archived-work-items/", status=404, json={"error": "Not found"})
    with pytest.raises(HttpError) as caught:
        archive_tool(action="list_archived", project_id="project-1")
    assert caught.value.status_code == 404
