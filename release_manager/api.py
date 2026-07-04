"""Server-side API for Release Manager.

Bridges the Frappe Desk (DocTypes, buttons, scheduler) to the ``release_tests``
execution engine. The engine does the HTTP work against target sites; this
module turns its plain-dict results into Test Result records.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

import frappe
from frappe.utils import now_datetime

_STEP_TO_RESULT = {"pass": "Passed", "fail": "Failed", "skip": "Skipped"}


# --------------------------------------------------------------------- helpers
def _site_config(site_doc) -> dict:
    """Build the engine's site-config dict from a Testing Site document."""
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
    from release_tests import api as engine

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
        if frappe.db.exists("Test Case Group", group_name):
            continue
        group = frappe.new_doc("Test Case Group")
        group.group_name = group_name
        group.description = f"Auto-seeded: all {app} test cases."
        for case in cases:
            group.append("test_cases", {"test_case": case})
        group.insert(ignore_permissions=True)
        created += 1
    return created


@frappe.whitelist()
def run_group(site: str, group: str, trigger: str = "Manual") -> str:
    """Create + queue a Release Test for every Test Case in a group."""
    group_doc = frappe.get_doc("Test Case Group", group)
    run = frappe.new_doc("Release Test")
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
    """Detect installed apps + versions for a Testing Site and store the result."""
    from release_tests import api as engine

    doc = frappe.get_doc("Testing Site", site)
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
    """Queue execution of a Release Test in the background."""
    doc = frappe.get_doc("Release Test", run)
    doc.db_set("status", "Queued")
    frappe.db.commit()
    frappe.enqueue(
        "release_manager.api.execute_run", queue="long", timeout=1500, run=run, enqueue_after_commit=True
    )
    return True


def execute_run(run: str) -> None:
    """Run all selected suites for a Release Test's site and record results."""
    from release_tests import api as engine

    doc = frappe.get_doc("Release Test", run)
    doc.db_set("status", "Running")
    doc.db_set("started_at", now_datetime())
    frappe.db.commit()

    # Re-running a Run replaces its previous results.
    frappe.db.delete("Test Result", {"run": run})

    site = frappe.get_doc("Testing Site", doc.site)
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
        res = frappe.new_doc("Test Result")
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
        # Stream progress so the dashboard terminal updates as suites finish.
        doc.db_set("log", "\n".join(log_lines), commit=True)

    doc.db_set("total_steps", sum(totals.values()))
    doc.db_set("passed", totals.get("pass", 0))
    doc.db_set("failed", totals.get("fail", 0))
    doc.db_set("skipped", totals.get("skip", 0))
    doc.db_set("transactions_created", result.get("transactions", 0))
    doc.db_set("detected_apps", json.dumps(result.get("versions", {}), indent=1))
    doc.db_set("status", "Failed" if any_fail and not any_pass else "Partial" if any_fail else "Passed")
    doc.db_set("finished_at", now_datetime())
    doc.db_set("log", "\n".join(log_lines) or "No applicable suites ran.")
    frappe.db.commit()


# -------------------------------------------------------------- UI (Cypress) run
_UI_TESTS_DEFAULT = os.path.expanduser("~/release_tests/ui")
_CY_STATE = {"passed": "pass", "failed": "fail", "pending": "skip", "skipped": "skip"}


def _ui_tests_path() -> str:
    return frappe.conf.get("release_ui_tests_path") or _UI_TESTS_DEFAULT


def _node_binary() -> str:
    for cand in (shutil.which("node"), "/opt/homebrew/bin/node", "/usr/local/bin/node"):
        if cand and os.path.exists(cand):
            return cand
    frappe.throw("Node.js not found — install it or set it on the worker's PATH.")


def _cypress_env(site_doc) -> dict:
    """Forward the site's URL + login credentials to the Cypress specs."""
    env = dict(os.environ)
    env["CYPRESS_BASE_URL"] = site_doc.base_url
    if site_doc.auth_type == "login":
        if site_doc.username:
            env["CYPRESS_ADMIN_USER"] = site_doc.username
        password = site_doc.get_password("password") if site_doc.password else None
        if password:
            env["CYPRESS_ADMIN_PASSWORD"] = password
    return env


@frappe.whitelist()
def run_ui_test(site: str, headed: int = 1) -> str:
    """Create + queue a UI (Cypress) Release Test for the site's Frappe version."""
    site_doc = frappe.get_doc("Testing Site", site)
    version = site_doc.frappe_version or "v16"
    run = frappe.new_doc("Release Test")
    run.site = site
    run.layer = "UI"
    run.trigger = "Manual"
    run.run_title = f"UI Tests ({version}) — {site}"
    run.insert(ignore_permissions=True)
    run.db_set("status", "Queued")
    frappe.enqueue(
        "release_manager.api.execute_ui_run",
        queue="long",
        timeout=1500,
        run=run.name,
        headed=int(headed),
        enqueue_after_commit=True,
    )
    frappe.db.commit()
    return run.name


def execute_ui_run(run: str, headed: int = 1) -> None:
    """Shell out to Cypress for the site's version and record UI Test Results."""
    doc = frappe.get_doc("Release Test", run)
    doc.db_set("status", "Running")
    doc.db_set("started_at", now_datetime())
    frappe.db.delete("Test Result", {"run": run})
    frappe.db.commit()

    site_doc = frappe.get_doc("Testing Site", doc.site)
    version = site_doc.frappe_version or "v16"
    ui_path = _ui_tests_path()
    result_file = os.path.join(tempfile.gettempdir(), f"cy-{run}.json")

    env = _cypress_env(site_doc)
    env.update(
        {"SPEC_DIR": f"cypress/e2e/{version}", "RESULT_FILE": result_file, "HEADED": "1" if int(headed) else "0"}
    )
    doc.db_set(
        "log", f"Launching Cypress ({version}, {'headed' if int(headed) else 'headless'}) in {ui_path}…", commit=True
    )

    try:
        proc = subprocess.run(
            [_node_binary(), "run.js"], cwd=ui_path, env=env, capture_output=True, text=True, timeout=1200
        )
    except Exception as exc:  # noqa: BLE001
        doc.db_set("status", "Failed")
        doc.db_set("log", f"Failed to launch Cypress: {exc}")
        doc.db_set("finished_at", now_datetime())
        frappe.db.commit()
        return

    data = {}
    if os.path.exists(result_file):
        with open(result_file) as handle:
            data = json.load(handle)
    _record_ui_results(doc, version, data, proc)


def _GUI_HINT() -> str:
    return (
        "Cypress could not start a browser. On macOS the bench must be started from a "
        "GUI Terminal session (run `bench start` in Terminal.app), not a headless/SSH "
        "context — Electron needs a window session even in headless mode. Start the bench "
        "there and re-run. (For unattended runs, use the Linux CI workflow.)"
    )


def _record_ui_results(doc, version: str, data: dict, proc) -> None:
    if data.get("error") or (not data.get("specs") and proc.returncode):
        raw = data.get("error") or (proc.stderr or proc.stdout or "Cypress run failed")
        launch_failed = any(
            marker in raw
            for marker in ("Could not find Cypress test run results", "no-sandbox", "release-test")
        )
        message = (_GUI_HINT() + "\n\n---\n" + raw) if launch_failed else raw
        doc.db_set("status", "Failed")
        doc.db_set("log", message[:5000])
        doc.db_set("finished_at", now_datetime())
        frappe.db.commit()
        return

    totals = {"pass": 0, "fail": 0, "skip": 0}
    log_lines: list[str] = []
    any_fail = any_pass = False

    for spec in data.get("specs", []):
        errs = []
        res = frappe.new_doc("Test Result")
        res.run = doc.name
        res.site = doc.site
        res.layer = "UI"
        res.suite = spec.get("spec")
        res.test_case = spec.get("spec")
        res.app_version = version
        spec_fail = spec_pass = False
        duration = 0
        for test in spec.get("tests", []):
            status = _CY_STATE.get(test.get("state"), "skip")
            totals[status] += 1
            duration += int(test.get("duration") or 0)
            res.append(
                "steps",
                {
                    "suite": spec.get("spec"),
                    "step": test.get("title"),
                    "status": status,
                    "duration_ms": int(test.get("duration") or 0),
                    "error": test.get("error"),
                },
            )
            if status == "fail":
                spec_fail = True
                errs.append(f"{test.get('title')}: {test.get('error')}")
            elif status == "pass":
                spec_pass = True
        res.duration_ms = duration
        res.status = "Failed" if spec_fail and not spec_pass else "Partial" if spec_fail else "Passed"
        res.error = "\n".join(e for e in errs if e)
        res.insert(ignore_permissions=True)
        log_lines.append(f"[{res.status}] {spec.get('spec')}")
        any_fail = any_fail or spec_fail
        any_pass = any_pass or spec_pass
        doc.db_set("log", "\n".join(log_lines), commit=True)

    doc.db_set("total_steps", sum(totals.values()))
    doc.db_set("passed", totals["pass"])
    doc.db_set("failed", totals["fail"])
    doc.db_set("skipped", totals["skip"])
    doc.db_set("status", "Failed" if any_fail and not any_pass else "Partial" if any_fail else "Passed")
    doc.db_set("finished_at", now_datetime())
    videos = [s["video"] for s in data.get("specs", []) if s.get("video")]
    tail = ("\n\nVideos:\n" + "\n".join(videos)) if videos else ""
    doc.db_set("log", ("\n".join(log_lines) or "No specs ran.") + tail)
    frappe.db.commit()


# ----------------------------------------------------------------- plans + cron
@frappe.whitelist()
def run_plan(plan: str, trigger: str = "Manual") -> list[str]:
    """Create + queue one Release Test per site in a Test Plan."""
    p = frappe.get_doc("Smoke Test Plan", plan)
    case_links = [c.test_case for c in p.cases]
    runs = []
    for plan_site in p.sites:
        run = frappe.new_doc("Release Test")
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
    """Create + queue a Release Test from a group, an explicit case list, or all applicable.

    Used by the Vue UI's New Run / re-run flows. ``test_cases`` may be a JSON string.
    """
    run = frappe.new_doc("Release Test")
    run.site = site
    run.trigger = "Manual"

    cases: list[str] = []
    if group:
        group_doc = frappe.get_doc("Test Case Group", group)
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
def dashboard_stats() -> dict:
    """Aggregate counters for the Release Manager dashboard."""
    by_status: dict[str, int] = {}
    for row in frappe.db.sql(
        "select status, count(name) as n from `tabTest Result` group by status", as_dict=True
    ):
        by_status[row.status] = row.n
    by_layer: dict[str, int] = {}
    for row in frappe.db.sql(
        "select coalesce(layer,'API') as layer, count(name) as n from `tabTest Result`"
        " where status != 'Skipped' group by layer",
        as_dict=True,
    ):
        by_layer[row.layer] = row.n
    transactions = frappe.db.sql(
        "select coalesce(sum(transactions_created), 0) from `tabRelease Test`"
    )[0][0]
    return {
        "runs": frappe.db.count("Release Test"),
        "tests_run": sum(n for s, n in by_status.items() if s != "Skipped"),
        "transactions": int(transactions or 0),
        "passed": by_status.get("Passed", 0),
        "failed": by_status.get("Failed", 0),
        "skipped": by_status.get("Skipped", 0),
        "partial": by_status.get("Partial", 0),
        "api_tests": by_layer.get("API", 0),
        "ui_tests": by_layer.get("UI", 0),
    }


@frappe.whitelist()
def rerun(run: str) -> str:
    """Clone a run's site + test cases into a fresh Release Test and queue it.

    UI runs re-run through the Cypress path so "Run again" repeats the browser test
    instead of falling back to the API engine.
    """
    src = frappe.get_doc("Release Test", run)
    if src.layer == "UI":
        return run_ui_test(src.site)
    new = frappe.new_doc("Release Test")
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
