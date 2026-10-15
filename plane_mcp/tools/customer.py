"""Customers in the workspace, and the work items linked to them."""

from __future__ import annotations

from typing import Literal

from fastmcp import FastMCP
from plane.models.customers import (
    CreateCustomer,
    Customer,
    CustomerAccessUpdate,
    CustomerAttachment,
    CustomerAttachmentUpload,
    CustomerAttachmentUploadResponse,
    CustomerProject,
    CustomerWorkItem,
    ManageCustomerWorkItems,
    PaginatedCustomerResponse,
    ReplaceCustomerProjects,
    UpdateCustomer,
)

from plane_mcp.client import get_plane_client_context
from plane_mcp.toolkit import (
    Action,
    build_annotations,
    build_description,
    coerce_list,
    missing,
    needs,
    opt,
    page_params,
)

NAME = "customer"
TITLE = "Customers"

STAGES = ("lead", "sales_qualified_lead", "contract_negotiation", "closed_won", "closed_lost")
CONTRACT_STATUSES = ("active", "pre_contract", "signed", "inactive")

ACTIONS = (
    Action("list", (), ("query", "cursor", "per_page"), read=True),
    Action("retrieve", ("customer_id",), read=True),
    Action(
        "create",
        ("name",),
        (
            "description_html",
            "email",
            "website_url",
            "domain",
            "employees",
            "stage",
            "contract_status",
            "revenue",
            "external_source",
            "external_id",
            "project_ids",
        ),
        note="upsert: matches on external_source + external_id, else on name, so it never duplicates",
    ),
    Action(
        "update",
        ("customer_id",),
        (
            "name",
            "description_html",
            "email",
            "website_url",
            "domain",
            "employees",
            "stage",
            "contract_status",
            "revenue",
            "external_source",
            "external_id",
            "project_ids",
        ),
        note="only the fields you pass are changed",
    ),
    Action(
        "delete",
        (),
        ("customer_id", "external_source", "external_id"),
        note="address by customer_id, or by external_source plus external_id",
        destructive=True,
    ),
    Action("list_workitems", ("customer_id",), ("customer_request_id", "search"), read=True),
    Action(
        "manage_workitems",
        ("customer_id",),
        ("link_ids", "unlink_ids", "customer_request_id"),
        note="pass at least one of link_ids or unlink_ids; returns nothing, read back with list_workitems",
    ),
    Action("list_projects", ("customer_id",), read=True),
    Action(
        "set_projects",
        ("customer_id", "project_ids"),
        note="replaces the linked projects",
    ),
    Action(
        "regenerate_access_key",
        ("customer_id",),
        note="returns the new key once",
    ),
    Action(
        "update_access",
        ("customer_id",),
        ("access_revoked", "access_expires_at"),
        note="revoke, restore, or set expiry",
    ),
    Action("list_attachments", ("customer_id",), read=True),
    Action(
        "upload_attachment",
        ("customer_id", "name", "file_type", "size"),
        note="presigned upload, then complete_attachment",
    ),
    Action("complete_attachment", ("customer_id", "asset_id")),
    Action("delete_attachment", ("customer_id", "asset_id"), destructive=True),
)

FOOTER = (
    'domain is the customer\'s industry, shown as "Industry" in Plane -- the website goes in '
    f"website_url. stage renders as one of: {', '.join(STAGES)}. contract_status renders as one "
    f"of: {', '.join(CONTRACT_STATUSES)}. Both are stored free-form; anything else is kept but "
    "not displayed. revenue is annual revenue as a string. project_ids is comma-separated. "
    "file_type is a MIME type, size is bytes, and access_expires_at is an ISO date."
)

LEGACY = {
    "list_customers": "list",
    "retrieve_customer": "retrieve",
    "create_customer": "create",
    "update_customer": "update",
    "delete_customer": "delete",
    "list_customer_work_items": "list_workitems",
}

LEGACY_UNMAPPED = {
    "manage_customer_work_items": "took action='link'|'unlink', which collides with the dispatch "
    "key: use manage_workitems with link_ids or unlink_ids",
}


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name=NAME,
        description=build_description("Customers in the workspace.", ACTIONS, FOOTER),
        annotations=build_annotations(TITLE, ACTIONS),
    )
    def customer(
        action: Literal[
            "list",
            "retrieve",
            "create",
            "update",
            "delete",
            "list_workitems",
            "manage_workitems",
            "list_projects",
            "set_projects",
            "regenerate_access_key",
            "update_access",
            "list_attachments",
            "upload_attachment",
            "complete_attachment",
            "delete_attachment",
        ],
        customer_id: str = "",
        customer_request_id: str = "",
        name: str = "",
        description_html: str = "",
        email: str = "",
        website_url: str = "",
        domain: str = "",
        employees: int = 0,
        stage: str = "",
        contract_status: str = "",
        revenue: str = "",
        link_ids: str = "",
        unlink_ids: str = "",
        search: str = "",
        query: str = "",
        external_source: str = "",
        external_id: str = "",
        project_ids: str = "",
        access_revoked: bool | None = None,
        access_expires_at: str = "",
        file_type: str = "",
        size: int = 0,
        asset_id: str = "",
        cursor: str = "",
        per_page: int = 0,
    ) -> (
        Customer
        | PaginatedCustomerResponse
        | list[CustomerWorkItem]
        | list[CustomerProject]
        | list[CustomerAttachment]
        | CustomerAttachmentUploadResponse
        | str
        | None
    ):
        client, workspace_slug = get_plane_client_context()
        customers = client.customers

        if action == "list":
            return customers.list(workspace_slug=workspace_slug, params=page_params(cursor, per_page, query=query))

        if action == "create":
            if not name:
                return missing(action, "name")
            return customers.create(
                workspace_slug=workspace_slug,
                data=CreateCustomer(
                    name=name,
                    description_html=opt(description_html),
                    email=opt(email),
                    website_url=opt(website_url),
                    domain=opt(domain),
                    employees=opt(employees),
                    stage=opt(stage),
                    contract_status=opt(contract_status),
                    revenue=opt(revenue),
                    external_source=opt(external_source),
                    external_id=opt(external_id),
                    project_ids=coerce_list(project_ids),
                ),
            )

        if action == "delete":
            if not customer_id and not (external_source and external_id):
                return missing(action, "customer_id (or both external_source and external_id)")
            customers.delete(
                workspace_slug=workspace_slug,
                customer_id=opt(customer_id),
                external_source=opt(external_source),
                external_id=opt(external_id),
            )
            return None

        if not customer_id:
            return missing(action, "customer_id")

        if action == "retrieve":
            return customers.retrieve(workspace_slug=workspace_slug, customer_id=customer_id)

        if action == "update":
            return customers.update(
                workspace_slug=workspace_slug,
                customer_id=customer_id,
                data=UpdateCustomer(
                    name=opt(name),
                    description_html=opt(description_html),
                    email=opt(email),
                    website_url=opt(website_url),
                    domain=opt(domain),
                    employees=opt(employees),
                    stage=opt(stage),
                    contract_status=opt(contract_status),
                    revenue=opt(revenue),
                    external_source=opt(external_source),
                    external_id=opt(external_id),
                    project_ids=coerce_list(project_ids),
                ),
            )

        work_items = customers.work_items

        if action == "list_workitems":
            return work_items.list(
                workspace_slug=workspace_slug,
                customer_id=customer_id,
                customer_request_id=opt(customer_request_id),
                search=opt(search),
            )

        if action == "manage_workitems":
            link = coerce_list(link_ids)
            unlink = coerce_list(unlink_ids)
            if not link and not unlink:
                return missing(action, "link_ids or unlink_ids")
            work_items.manage(
                workspace_slug=workspace_slug,
                customer_id=customer_id,
                data=ManageCustomerWorkItems(
                    link_ids=link,
                    unlink_ids=unlink,
                    customer_request_id=opt(customer_request_id),
                ),
            )
            return None

        if action == "list_projects":
            return customers.projects.list(workspace_slug=workspace_slug, customer_id=customer_id)

        if action == "set_projects":
            ids = coerce_list(project_ids)
            if not ids:
                return missing(action, "project_ids")
            return customers.projects.replace(
                workspace_slug=workspace_slug,
                customer_id=customer_id,
                data=ReplaceCustomerProjects(project_ids=ids),
            )

        if action == "regenerate_access_key":
            return customers.access.regenerate_key(workspace_slug=workspace_slug, customer_id=customer_id)

        if action == "update_access":
            if access_revoked is None and not access_expires_at:
                return missing(action, "access_revoked or access_expires_at")
            return customers.access.update(
                workspace_slug=workspace_slug,
                customer_id=customer_id,
                data=CustomerAccessUpdate(
                    access_revoked=access_revoked,
                    access_expires_at=opt(access_expires_at),
                ),
            )

        attachments = customers.attachments

        if action == "list_attachments":
            return attachments.list(workspace_slug=workspace_slug, customer_id=customer_id)

        if action == "upload_attachment":
            if error := needs(action, name=name, file_type=file_type, size=size):
                return error
            return attachments.create(
                workspace_slug=workspace_slug,
                customer_id=customer_id,
                data=CustomerAttachmentUpload(name=name, type=file_type, size=size),
            )

        if not asset_id:
            return missing(action, "asset_id")

        if action == "complete_attachment":
            attachments.complete(workspace_slug=workspace_slug, customer_id=customer_id, asset_id=asset_id)
            return None

        attachments.delete(workspace_slug=workspace_slug, customer_id=customer_id, asset_id=asset_id)
        return None
