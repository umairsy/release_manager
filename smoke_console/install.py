"""Post-install setup: load the test-case catalog and build dashboard widgets."""

from __future__ import annotations

import json

import frappe


def after_install() -> None:
    from smoke_console.api import sync_catalog

    try:
        sync_catalog()
    except Exception:
        frappe.log_error(title="smoke_console: catalog sync on install failed")

    _ensure_number_card(
        "Smoke - Open Failures",
        "Test Result",
        filters=[["Test Result", "status", "=", "Failed"], ["Test Result", "action_status", "in", ["Open", "Investigating"]]],
    )
    _ensure_number_card(
        "Smoke - Results Logged",
        "Test Result",
        filters=[],
    )
    _ensure_status_chart()
    frappe.db.commit()


def _ensure_number_card(name: str, doctype: str, filters: list) -> None:
    if frappe.db.exists("Number Card", name):
        return
    try:
        frappe.get_doc(
            {
                "doctype": "Number Card",
                "name": name,
                "label": name,
                "type": "Document Type",
                "document_type": doctype,
                "function": "Count",
                "is_public": 1,
                "filters_json": json.dumps(filters),
            }
        ).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(title=f"smoke_console: number card {name} failed")


def _ensure_status_chart() -> None:
    name = "Smoke - Results by Status"
    if frappe.db.exists("Dashboard Chart", name):
        return
    try:
        frappe.get_doc(
            {
                "doctype": "Dashboard Chart",
                "name": name,
                "chart_name": name,
                "chart_type": "Group By",
                "document_type": "Test Result",
                "group_by_type": "Count",
                "group_by_based_on": "status",
                "type": "Donut",
                "is_public": 1,
                "filters_json": "[]",
            }
        ).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(title="smoke_console: status chart failed")
