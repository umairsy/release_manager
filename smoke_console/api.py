"""Server-side API for Smoke Console.

Bridges the Frappe Desk (DocTypes, buttons, scheduler) to the ``frappe_smoke``
execution engine. The engine does the HTTP work against target sites; this
module turns its plain-dict results into Smoke Result records.
"""

from __future__ import annotations

import json

import frappe
from frappe.utils import now_datetime

_STEP_TO_RESULT = {"pass": "Passed", "fail": "Failed", "skip": "Skipped"}


# --------------------------------------------------------------------- helpers
def _site_config(site_doc) -> dict:
    """Build the engine's site-config dict from a Smoke Site document."""
    cfg = {
        "label": site_doc.name,
        "url": site_doc.base_url,
        "host_header": site_doc.host_header or None,
        "auth": site_doc.auth_type,
        "username": site_doc.username,
        "api_key": site_doc.api_key,
    }
    if site_doc.auth_type == "login":
        cfg["password"] = site_doc.get_password("password") if site_doc.password else None
    else:
        cfg["api_secret"] = site_doc.get_password("api_secret") if site_doc.api_secret else None
    return cfg


def _suites_for_run(run_doc) -> list[str] | None:
    """Resolve the selected Test Cases to engine suite names (None = all)."""
    if not run_doc.test_cases:
        return None
    suites = []
    for row in run_doc.test_cases:
        suite = frappe.db.get_value("Smoke Test Case", row.test_case, "suite")
        if suite:
            suites.append(suite)
    return suites or None


# ------------------------------------------------------------- catalog + sites
@frappe.whitelist()
def sync_catalog() -> int:
    """Upsert Smoke Test Case records from the engine's suite catalog."""
    from frappe_smoke import api as engine

    count = 0
    for entry in engine.catalog():
        preview = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(entry["steps"]))
        existing = frappe.db.get_value("Smoke Test Case", {"suite": entry["suite"]}, "name")
        doc = (
            frappe.get_doc("Smoke Test Case", existing)
            if existing
            else frappe.new_doc("Smoke Test Case")
        )
        if not existing:
            doc.test_case_name = entry["suite"]
        doc.suite = entry["suite"]
        doc.required_app = entry["required_app"]
        doc.description = entry["description"]
        doc.steps_preview = preview
        doc.save(ignore_permissions=True)
        count += 1
    seed_example_groups()
    frappe.db.commit()
    return count


@frappe.whitelist()
def seed_example_groups() -> int:
    """Create one curated group per app from existing Test Cases' required_app.

    Idempotent and non-destructive: only creates a group if it doesn't exist, so
    it never overwrites groups the user has hand-edited. Gives sensible defaults
    like "ERPNext - Distribution" (all erpnext cases) out of the box.
    """
    labels = {
        "erpnext": "ERPNext - Distribution",
        "hrms": "Frappe HR",
        "frappe": "Framework",
    }
    by_app: dict[str, list[str]] = {}
    for case in frappe.get_all(
        "Smoke Test Case", filters={"enabled": 1}, fields=["name", "required_app"]
    ):
        by_app.setdefault(case.required_app or "other", []).append(case.name)

    created = 0
    for app, cases in by_app.items():
        group_name = labels.get(app, app.replace("_", " ").title())
        if frappe.db.exists("Smoke Test Group", group_name):
            continue
        group = frappe.new_doc("Smoke Test Group")
        group.group_name = group_name
        group.description = f"Auto-seeded: all {app} test cases."
        for case in cases:
            group.append("test_cases", {"test_case": case})
        group.insert(ignore_permissions=True)
        created += 1
    return created


@frappe.whitelist()
def run_group(site: str, group: str, trigger: str = "Manual") -> str:
    """Create + queue a Smoke Run for every Test Case in a group."""
    group_doc = frappe.get_doc("Smoke Test Group", group)
    run = frappe.new_doc("Smoke Run")
    run.run_title = f"{group_doc.group_name} — {site}"
    run.site = site
    run.trigger = trigger
    for row in group_doc.test_cases:
        run.append("test_cases", {"test_case": row.test_case})
    run.insert(ignore_permissions=True)
    run_now(run.name)
    frappe.db.commit()
    return run.name


@frappe.whitelist()
def test_connection(site: str) -> dict:
    """Detect installed apps + versions for a Smoke Site and store the result."""
    from frappe_smoke import api as engine

    doc = frappe.get_doc("Smoke Site", site)
    try:
        versions = engine.detect_site(_site_config(doc))
        summary = "OK — " + ", ".join(
            f"{a} {v.get('version') or v.get('branch') or '?'}" for a, v in sorted(versions.items())
        )
        doc.db_set("last_status", summary)
        doc.db_set("last_detected_apps", json.dumps(versions, indent=1))
        frappe.db.commit()
        return {"ok": True, "status": summary}
    except Exception as exc:  # noqa: BLE001
        doc.db_set("last_status", f"FAILED — {exc}")
        frappe.db.commit()
        return {"ok": False, "error": str(exc)}


# ------------------------------------------------------------------- run a test
@frappe.whitelist()
def run_now(run: str) -> bool:
    """Queue execution of a Smoke Run in the background."""
    doc = frappe.get_doc("Smoke Run", run)
    doc.db_set("status", "Queued")
    frappe.db.commit()
    frappe.enqueue(
        "smoke_console.api.execute_run", queue="long", timeout=1500, run=run, enqueue_after_commit=True
    )
    return True


def execute_run(run: str) -> None:
    """Run all selected suites for a Smoke Run's site and record results."""
    from frappe_smoke import api as engine

    doc = frappe.get_doc("Smoke Run", run)
    doc.db_set("status", "Running")
    doc.db_set("started_at", now_datetime())
    frappe.db.commit()

    # Re-running a Run replaces its previous results.
    frappe.db.delete("Smoke Result", {"run": run})

    site = frappe.get_doc("Smoke Site", doc.site)
    suites = _suites_for_run(doc)

    try:
        result = engine.run_site(_site_config(site), suites=suites)
    except Exception as exc:  # noqa: BLE001
        doc.db_set("status", "Failed")
        doc.db_set("log", f"Connection/execution error: {exc}")
        doc.db_set("finished_at", now_datetime())
        frappe.db.commit()
        return

    if result.get("error"):
        doc.db_set("status", "Failed")
        doc.db_set("log", result["error"])
        doc.db_set("finished_at", now_datetime())
        frappe.db.commit()
        return

    totals = {"pass": 0, "fail": 0, "skip": 0}
    log_lines = []
    any_fail = any_pass = False

    for suite in result.get("suites", []):
        errs = []
        res = frappe.new_doc("Smoke Result")
        res.run = run
        res.site = doc.site
        res.suite = suite["suite"]
        res.test_case = suite["suite"]
        res.app_version = suite.get("app_version")
        res.status = _STEP_TO_RESULT.get(suite["status"], "Skipped")
        res.duration_ms = sum(st["duration_ms"] for st in suite["steps"])
        for st in suite["steps"]:
            totals[st["status"]] = totals.get(st["status"], 0) + 1
            res.append(
                "steps",
                {
                    "suite": st["suite"],
                    "step": st["step"],
                    "status": st["status"],
                    "duration_ms": st["duration_ms"],
                    "error": st.get("error"),
                },
            )
            if st.get("error"):
                errs.append(f"{st['step']}: {st['error']}")
        res.error = "\n".join(errs)
        res.insert(ignore_permissions=True)

        log_lines.append(f"[{res.status}] {suite['suite']} ({suite.get('app_version') or '-'})")
        any_fail = any_fail or suite["status"] == "fail"
        any_pass = any_pass or suite["status"] == "pass"

    doc.db_set("total_steps", sum(totals.values()))
    doc.db_set("passed", totals.get("pass", 0))
    doc.db_set("failed", totals.get("fail", 0))
    doc.db_set("skipped", totals.get("skip", 0))
    doc.db_set("detected_apps", json.dumps(result.get("versions", {}), indent=1))
    doc.db_set("status", "Failed" if any_fail and not any_pass else "Partial" if any_fail else "Passed")
    doc.db_set("finished_at", now_datetime())
    doc.db_set("log", "\n".join(log_lines) or "No applicable suites ran.")
    frappe.db.commit()


# ----------------------------------------------------------------- plans + cron
@frappe.whitelist()
def run_plan(plan: str, trigger: str = "Manual") -> list[str]:
    """Create + queue one Smoke Run per site in a Test Plan."""
    p = frappe.get_doc("Smoke Test Plan", plan)
    case_links = [c.test_case for c in p.cases]
    runs = []
    for plan_site in p.sites:
        run = frappe.new_doc("Smoke Run")
        run.run_title = f"{p.plan_name} — {plan_site.site}"
        run.site = plan_site.site
        run.plan = plan
        run.trigger = trigger
        for tc in case_links:
            run.append("test_cases", {"test_case": tc})
        run.insert(ignore_permissions=True)
        run_now(run.name)
        runs.append(run.name)
    frappe.db.commit()
    return runs


@frappe.whitelist()
def create_and_run(site: str, group: str | None = None, test_cases=None, title: str | None = None) -> str:
    """Create + queue a Smoke Run from a group, an explicit case list, or all applicable.

    Used by the Vue UI's New Run / re-run flows. ``test_cases`` may be a JSON string.
    """
    run = frappe.new_doc("Smoke Run")
    run.site = site
    run.trigger = "Manual"

    cases: list[str] = []
    if group:
        group_doc = frappe.get_doc("Smoke Test Group", group)
        cases = [row.test_case for row in group_doc.test_cases]
        run.run_title = title or f"{group_doc.group_name} — {site}"
    elif test_cases:
        cases = json.loads(test_cases) if isinstance(test_cases, str) else list(test_cases)
        run.run_title = title or f"{', '.join(cases)} — {site}"
    else:
        run.run_title = title or f"All applicable — {site}"

    for case in cases:
        run.append("test_cases", {"test_case": case})
    run.insert(ignore_permissions=True)
    run_now(run.name)
    frappe.db.commit()
    return run.name


@frappe.whitelist()
def rerun(run: str) -> str:
    """Clone a run's site + test cases into a fresh Smoke Run and queue it."""
    src = frappe.get_doc("Smoke Run", run)
    new = frappe.new_doc("Smoke Run")
    new.site = src.site
    new.run_title = src.run_title
    new.trigger = "Manual"
    for row in src.test_cases:
        new.append("test_cases", {"test_case": row.test_case})
    new.insert(ignore_permissions=True)
    run_now(new.name)
    frappe.db.commit()
    return new.name


def _run_scheduled(frequency: str) -> None:
    plans = frappe.get_all(
        "Smoke Test Plan", filters={"enabled": 1, "frequency": frequency}, pluck="name"
    )
    for plan in plans:
        run_plan(plan, trigger="Scheduled")


def run_hourly() -> None:
    _run_scheduled("Hourly")


def run_daily() -> None:
    _run_scheduled("Daily")


def run_weekly() -> None:
    _run_scheduled("Weekly")
