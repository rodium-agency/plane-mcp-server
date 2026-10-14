"""Subscriptions to work items, including a durable unsubscribe."""

from __future__ import annotations

import pytest


@pytest.fixture
def workitem_subscriber(registered, spy):
    return registered["workitem_subscriber"].fn, spy


def test_list_reads_the_work_item_subscribers(workitem_subscriber):
    tool, spy = workitem_subscriber

    tool(action="list", project_id="project-1", workitem_id="item-1", cursor="cursor-1", per_page=20)

    call = spy.recorder.only()
    assert call.method == "work_items.subscribers.list"
    assert call.kwargs["project_id"] == "project-1"
    assert call.kwargs["work_item_id"] == "item-1"
    assert call.kwargs["params"] == {"cursor": "cursor-1", "per_page": 20}


def test_subscribe_defaults_to_the_api_key_user(workitem_subscriber):
    tool, spy = workitem_subscriber

    tool(action="subscribe", project_id="project-1", workitem_id="item-1")

    call = spy.recorder.only()
    assert call.method == "work_items.subscribers.create"
    assert call.kwargs["subscriber"] is None


def test_subscribe_can_target_another_member(workitem_subscriber):
    tool, spy = workitem_subscriber

    tool(action="subscribe", project_id="project-1", workitem_id="item-1", subscriber="user-2")

    assert spy.recorder.only().kwargs["subscriber"] == "user-2"


def test_unsubscribe_defaults_to_me(workitem_subscriber):
    tool, spy = workitem_subscriber

    result = tool(action="unsubscribe", project_id="project-1", workitem_id="item-1")

    call = spy.recorder.only()
    assert call.method == "work_items.subscribers.delete"
    assert call.kwargs["subscriber"] == "me"
    assert result is None


def test_list_for_user_defaults_to_me(workitem_subscriber):
    tool, spy = workitem_subscriber

    tool(action="list_for_user")

    call = spy.recorder.only()
    assert call.method == "subscriptions.list"
    assert call.kwargs["params"]["subscriber"] == "me"
    assert "project_id" not in call.kwargs["params"]


def test_list_for_user_can_filter_by_project(workitem_subscriber):
    tool, spy = workitem_subscriber

    tool(action="list_for_user", subscriber="user-2", project_id="project-1", per_page=50)

    assert spy.recorder.only().kwargs["params"] == {
        "subscriber": "user-2",
        "project_id": "project-1",
        "per_page": 50,
    }


def test_unsubscribe_all_defaults_to_me(workitem_subscriber):
    tool, spy = workitem_subscriber

    tool(action="unsubscribe_all")

    call = spy.recorder.only()
    assert call.method == "subscriptions.delete"
    assert call.kwargs["params"] == {"subscriber": "me"}


def test_unsubscribe_all_can_filter_by_project(workitem_subscriber):
    tool, spy = workitem_subscriber

    tool(action="unsubscribe_all", subscriber="me", project_id="project-1")

    assert spy.recorder.only().kwargs["params"] == {"subscriber": "me", "project_id": "project-1"}
