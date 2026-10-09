"""State-time schedule and the durations an agent can read back."""

from __future__ import annotations

import pytest


@pytest.fixture
def project(registered, spy):
    return registered["project"].fn, spy


@pytest.fixture
def workitem_activity(registered, spy):
    return registered["workitem_activity"].fn, spy


def test_update_sends_the_state_time_schedule(project):
    tool, spy = project

    tool(
        action="update",
        project_id="project-1",
        state_time_tracking=True,
        state_time_start="10:00:00",
        state_time_end="18:30:00",
        state_time_days=[0, 2, 4],
    )

    data = spy.recorder.only().kwargs["data"]
    assert data.state_time_tracking is True
    assert data.state_time_start == "10:00:00"
    assert data.state_time_end == "18:30:00"
    assert data.state_time_days == [0, 2, 4]


def test_update_leaves_an_omitted_schedule_unchanged(project):
    tool, spy = project

    tool(action="update", project_id="project-1", name="Trofy")

    data = spy.recorder.only().kwargs["data"]
    assert data.state_time_tracking is None
    assert data.state_time_start is None
    assert data.state_time_end is None
    assert data.state_time_days is None


def test_state_durations_reads_the_work_item(workitem_activity):
    tool, spy = workitem_activity

    tool(action="state_durations", project_id="project-1", workitem_id="item-1")

    call = spy.recorder.only()
    assert call.method == "work_items.activities.state_durations"
    assert call.kwargs["project_id"] == "project-1"
    assert call.kwargs["work_item_id"] == "item-1"
