"""Who follows a work item, and the subscriptions of a user."""

from __future__ import annotations

from typing import Any, Literal

from fastmcp import FastMCP
from plane.models.work_items import SubscriptionBulkDelete, WorkItemSubscriber

from plane_mcp.client import get_plane_client_context
from plane_mcp.toolkit import Action, build_annotations, build_description, envelope, needs, opt, page_params

NAME = "workitem_subscriber"
TITLE = "Work item subscribers"

ACTIONS = (
    Action("list", ("project_id", "workitem_id"), ("cursor", "per_page"), read=True),
    Action(
        "subscribe",
        ("project_id", "workitem_id"),
        ("subscriber",),
        note="defaults to the API key user",
    ),
    Action(
        "unsubscribe",
        ("project_id", "workitem_id"),
        ("subscriber",),
        destructive=True,
        note="defaults to the API key user; a later assignment does not resubscribe",
    ),
    Action(
        "list_for_user",
        (),
        ("subscriber", "project_id", "cursor", "per_page"),
        read=True,
        note="defaults to the API key user",
    ),
    Action(
        "unsubscribe_all",
        (),
        ("subscriber", "project_id"),
        destructive=True,
        note="defaults to the API key user; every matching subscription in the workspace",
    ),
)

FOOTER = (
    "subscriber defaults to the API key user; pass me or a user id. "
    "A member manages only their own subscriptions. A project admin can manage another member of that project. "
    "unsubscribe writes a durable opt-out, so a later assignment does not subscribe them again. "
    "Mentions still notify. unsubscribe_all removes every matching subscription in the workspace; "
    "pass project_id to limit it to one project."
)

LEGACY: dict[str, str] = {}


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name=NAME,
        description=build_description("Who follows a work item, and a user's subscriptions.", ACTIONS, FOOTER),
        annotations=build_annotations(TITLE, ACTIONS),
    )
    def workitem_subscriber(
        action: Literal["list", "subscribe", "unsubscribe", "list_for_user", "unsubscribe_all"],
        project_id: str = "",
        workitem_id: str = "",
        subscriber: str = "",
        cursor: str = "",
        per_page: int = 0,
    ) -> dict[str, Any] | WorkItemSubscriber | SubscriptionBulkDelete | str | None:
        client, workspace_slug = get_plane_client_context()

        if action in ("list", "subscribe", "unsubscribe"):
            if error := needs(action, project_id=project_id, workitem_id=workitem_id):
                return error

        if action == "list":
            response = client.work_items.subscribers.list(
                workspace_slug=workspace_slug,
                project_id=project_id,
                work_item_id=workitem_id,
                params=page_params(cursor, per_page),
            )
            return envelope(response)

        if action == "subscribe":
            return client.work_items.subscribers.create(
                workspace_slug=workspace_slug,
                project_id=project_id,
                work_item_id=workitem_id,
                subscriber=opt(subscriber),
            )

        if action == "unsubscribe":
            client.work_items.subscribers.delete(
                workspace_slug=workspace_slug,
                project_id=project_id,
                work_item_id=workitem_id,
                subscriber=opt(subscriber) or "me",
            )
            return None

        target = opt(subscriber) or "me"
        if action == "list_for_user":
            response = client.subscriptions.list(
                workspace_slug=workspace_slug,
                params=page_params(cursor, per_page, subscriber=target, project_id=opt(project_id)),
            )
            return envelope(response)

        return client.subscriptions.delete(
            workspace_slug=workspace_slug,
            params=page_params(subscriber=target, project_id=opt(project_id)) or {"subscriber": target},
        )
