"""Requests raised by a customer."""

from __future__ import annotations

from typing import Literal

from fastmcp import FastMCP
from plane.models.customers import (
    CreateCustomerRequest,
    CustomerRequest,
    PaginatedCustomerRequestResponse,
    UpdateCustomerRequest,
)

from plane_mcp.client import get_plane_client_context
from plane_mcp.toolkit import (
    Action,
    build_annotations,
    build_description,
    coerce_list,
    missing,
    one_of,
    opt,
    page_params,
)

NAME = "customer_request"
TITLE = "Customer requests"

PRIORITIES = ("urgent", "high", "medium", "low")
REQUEST_TYPES = ("bug", "task", "other")

ACTIONS = (
    Action("list", ("customer_id",), ("query", "cursor", "per_page"), read=True),
    Action("retrieve", ("customer_id", "request_id"), read=True),
    Action(
        "create",
        ("customer_id", "name"),
        ("description_html", "link", "priority", "request_type", "project_id", "workitem_ids"),
        note="project_id with priority and request_type files an intake",
    ),
    Action(
        "update",
        ("customer_id", "request_id"),
        ("name", "description_html", "link", "priority", "request_type"),
        note="only the fields you pass are changed",
    ),
    Action("delete", ("customer_id", "request_id"), destructive=True),
)

FOOTER = (
    "link is a URL associated with the request. workitem_ids is never echoed back -- read the "
    "links with `customer list_workitems`. priority: urgent, high, medium, low. "
    "request_type: bug, task, other."
)

LEGACY = {
    "list_customer_requests": "list",
    "retrieve_customer_request": "retrieve",
    "create_customer_request": "create",
    "update_customer_request": "update",
    "delete_customer_request": "delete",
}


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name=NAME,
        description=build_description("Requests raised by a customer.", ACTIONS, FOOTER),
        annotations=build_annotations(TITLE, ACTIONS),
    )
    def customer_request(
        action: Literal["list", "retrieve", "create", "update", "delete"],
        customer_id: str = "",
        request_id: str = "",
        name: str = "",
        description_html: str = "",
        link: str = "",
        priority: str = "",
        request_type: str = "",
        project_id: str = "",
        workitem_ids: str = "",
        query: str = "",
        cursor: str = "",
        per_page: int = 0,
    ) -> CustomerRequest | PaginatedCustomerRequestResponse | str | None:
        client, workspace_slug = get_plane_client_context()

        if not customer_id:
            return missing(action, "customer_id")

        requests = client.customers.requests

        if action == "list":
            return requests.list(
                workspace_slug=workspace_slug,
                customer_id=customer_id,
                params=page_params(cursor, per_page, query=query),
            )

        if action == "create":
            if not name:
                return missing(action, "name")
            if error := one_of("priority", priority, PRIORITIES):
                return error
            if error := one_of("request_type", request_type, REQUEST_TYPES):
                return error
            return requests.create(
                workspace_slug=workspace_slug,
                customer_id=customer_id,
                data=CreateCustomerRequest(
                    name=name,
                    description_html=opt(description_html),
                    link=opt(link),
                    priority=opt(priority),
                    request_type=opt(request_type),
                    project_id=opt(project_id),
                    work_item_ids=coerce_list(workitem_ids),
                ),
            )

        if not request_id:
            return missing(action, "request_id")

        if action == "retrieve":
            return requests.retrieve(workspace_slug=workspace_slug, customer_id=customer_id, request_id=request_id)

        if action == "update":
            if error := one_of("priority", priority, PRIORITIES):
                return error
            if error := one_of("request_type", request_type, REQUEST_TYPES):
                return error
            return requests.update(
                workspace_slug=workspace_slug,
                customer_id=customer_id,
                request_id=request_id,
                data=UpdateCustomerRequest(
                    name=opt(name),
                    description_html=opt(description_html),
                    link=opt(link),
                    priority=opt(priority),
                    request_type=opt(request_type),
                ),
            )

        requests.delete(workspace_slug=workspace_slug, customer_id=customer_id, request_id=request_id)
        return None
