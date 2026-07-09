"""Repair dashboard widgets that still reference pre-rename DocType names.

`frappe.rename_doc` renames tables and Link fields, but it does not rewrite JSON
text fields such as a Number Card / Dashboard Chart ``filters_json``. Widgets
created under an old name (e.g. the "Open Failures" card built when the result
DocType was still ``Smoke Result``) therefore keep dangling references and render
broken on the workspace. This rewrites those references, idempotently.
"""

import frappe

# Every legacy -> current DocType rename this app has been through.
LEGACY_NAMES = {
    "Smoke Site": "Testing Site",
    "Smoke Run": "Release Test",
    "Smoke Result": "Test Result",
    "Smoke Test Group": "Test Case Group",
    "Smoke Test Case": "Release Test Case",
    "Smoke Test Plan": "Release Test Plan",
    "Smoke Plan Case": "Release Plan Case",
    "Smoke Plan Site": "Release Plan Site",
    "Smoke Step Result": "Release Step Result",
}


def _fix(doctype, field):
    for name in frappe.get_all(doctype, pluck="name"):
        val = frappe.db.get_value(doctype, name, field)
        if not val:
            continue
        new = val
        for old, cur in LEGACY_NAMES.items():
            new = new.replace(f'"{old}"', f'"{cur}"')
        if new != val:
            frappe.db.set_value(doctype, name, field, new, update_modified=False)


def execute():
    _fix("Number Card", "filters_json")
    _fix("Dashboard Chart", "filters_json")
    _fix("Dashboard Chart", "dynamic_filters_json")
