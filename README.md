# Release Manager (app package: `smoke_console`)

A Frappe app that is the **control plane / UI** for the
[`frappe_smoke`](../frappe_smoke) execution engine. It lets you register target
Frappe sites, keep a master catalog of test cases, run smoke tests (manually or
on a schedule), and review results with corrective-action tracking — from the
Frappe Desk or the Vue dashboard at **`/release`**.

> The product is branded **Release Manager**; the Python package, doctypes
> (`Smoke *`), and repo keep their original `smoke_console` names.

## Running against Frappe Cloud (or any remote site)

The engine is a pure external HTTP client, so no install is needed on the target.
To test a Frappe Cloud site:

1. On that site, create an **API key + secret** for a user with the needed roles
   (User → API Access → Generate Keys).
2. Add a **Smoke Site** with `base_url = https://<site>.frappe.cloud`,
   `auth_type = token`, and those `api_key`/`api_secret`. Leave Host header blank
   (real DNS). Click **Test Connection**, then run.

Token auth is verified working end-to-end (engine `use_token`).

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

## Test Groups

A **Smoke Test Group** bundles test cases so you can run a whole area at once. Running a
group (Desk "Run Group" button, or `smoke_console.api.run_group(site, group)`) creates one
Smoke Run for every case in the group. `sync_catalog` auto-seeds per-app groups (e.g.
"ERPNext - Distribution" = all erpnext cases); you can also curate your own, mixing apps.

## Web UI (`/smoke`)

A Vue single-page app (frappe-ui + Vite, in `frontend/`) served at
`http://<site>/smoke`, reusing the standard Frappe login. Views: **Runs list** → **New Run**
(pick a Site + a Group) → **Run detail** (live suites → steps, errors, and a corrective-action
/ re-run panel that updates while the run is in flight).

Build it (independent of `bench build`/esbuild):

```bash
cd frontend && yarn && yarn build      # outputs to smoke_console/public/frontend + www/smoke/index.html
# first time only, ensure the asset symlink exists:
ln -sfn $PWD/../smoke_console/public <bench>/sites/assets/smoke_console
```

Dev: `cd frontend && yarn dev` (Vite proxies `/api` to the bench).
