# Smoke Console

A Frappe app that is the **control plane / UI** for the
[`frappe_smoke`](../frappe_smoke) execution engine. It lets you register target
Frappe sites, keep a master catalog of test cases, run smoke tests (manually or
on a schedule), and review results with corrective-action tracking — all from
the Frappe Desk.

It runs on one local **control site** (e.g. `smoke.localhost`) and drives *other*
sites over HTTP via the engine, so it never has to be installed on the systems
under test. The same Site records later point at Frappe Cloud URLs with API
tokens — no rework.

## Concepts (DocTypes)

- **Smoke Site** — a target site: URL, Host header, and login or token auth.
  "Test Connection" detects installed apps + versions.
- **Smoke Test Case** — the test master, synced from the engine's suite catalog
  ("Sync Catalog"). Each maps to an engine suite (e.g. `erpnext`).
- **Smoke Test Plan** — a saved selection of sites + test cases with a frequency
  (Manual/Hourly/Daily/Weekly) for scheduled runs.
- **Smoke Run** — one execution: pick a Site, pick Test Cases, "Run Now". Runs in
  the background and records status + counts.
- **Smoke Result** — per run/site/suite outcome with step-by-step detail, an
  error log, and `corrective_action` + `action_status` fields to triage.

## Flow

1. Add Smoke Sites and click **Test Connection**.
2. **Sync Catalog** on Smoke Test Case to load available suites.
3. Create a Smoke Run → choose a Site + Test Cases → **Run Now**.
4. Watch status, then review Smoke Results; record corrective actions.
5. (Optional) Save a Smoke Test Plan and set a frequency for scheduled runs.

The **Smoke Console** Workspace gives shortcuts and pass/fail dashboard charts.

## Dev install

```bash
# engine into the bench env
benches/frappe-bench/env/bin/python -m pip install -e ~/frappe_smoke
# app into the bench, then on the control site
bench --site smoke.localhost install-app smoke_console
```
