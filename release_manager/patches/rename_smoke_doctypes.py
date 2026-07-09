"""Drop the legacy 'Smoke' brand from the DocType names.

Runs pre_model_sync so the DocTypes are renamed in the database *before* the
new JSON definitions are imported — otherwise sync would create fresh
'Release *' DocTypes and orphan the old 'Smoke *' tables and their data.
"""

import frappe

# (old name, new name) — masters first, then the child tables they contain.
RENAMES = [
    ("Smoke Test Case", "Release Test Case"),
    ("Smoke Test Plan", "Release Test Plan"),
    ("Smoke Plan Case", "Release Plan Case"),
    ("Smoke Plan Site", "Release Plan Site"),
    ("Smoke Step Result", "Release Step Result"),
]


def execute():
    for old, new in RENAMES:
        if frappe.db.exists("DocType", old) and not frappe.db.exists("DocType", new):
            frappe.rename_doc("DocType", old, new, force=True)
            frappe.flags.ignore_route_conflict_validation = True
