# Contributing to Release Manager

Release Manager is the **control plane / UI** for the
[`release_tests`](https://github.com/umairsy/release_tests) engine. It lets you
register target sites, keep a catalog of test cases, run release tests (manually
or on a schedule), and review results with corrective-action tracking — from the
Frappe Desk or the Vue dashboard at `/release`.

The product goal is to **catch regressions across Frappe app releases and
versions before they reach production**, and make triaging those failures fast.
Keep that in mind for every change.

## Golden rules

1. **Don't break existing data.** Do not rename or remove a DocType or field
   without a `frappe.rename_doc` migration patch in `patches.txt` (see
   `release_manager/patches/rename_smoke_doctypes.py` for the pattern).
2. **The engine is a dependency, not part of this app.** Behaviour that belongs
   to *how tests run* lives in `release_tests`; this app orchestrates, persists,
   and displays. Consider engine version compatibility when you touch `api.py`.
3. **Non-destructive on targets.** Anything that drives a target site must go
   through the engine's idempotent, non-destructive flows.
4. **Never commit credentials.** Site auth (passwords, API secrets) lives in
   DocType `Password` fields; never hard-code real credentials or commit them.

## Dev setup

```bash
# engine into the bench env
benches/frappe-bench/env/bin/python -m pip install -e ~/release_tests
# app into the bench, then on the control site
bench --site releasemanager.localhost install-app release_manager
```

Frontend (Vue single-page app in `frontend/`, built independently of `bench build`):

```bash
cd frontend && yarn && yarn build   # outputs to release_manager/public/frontend + www/release/index.html
cd frontend && yarn dev             # dev server; Vite proxies /api to the bench
```

## Before you open a PR

- Exercise a **real Release Test** against a Testing Site and confirm status,
  run detail, and results render correctly.
- If you changed the Vue UI, rebuild (`yarn build`) and attach screenshots.
- If you changed a DocType, confirm a fresh install *and* an in-place migrate
  both succeed.

## Pull requests

- Fork, branch, and open a PR against `main`.
- `main` is protected: **1 approving review** is required before merge. Merge
  rights are held by the maintainers.
- Fill in the PR template, especially the safety checklist, and include
  screenshots for any UI change.
