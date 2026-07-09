<!-- Thanks for contributing to Release Manager! -->

## What & why


## Type of change
- [ ] Desk / DocType change
- [ ] Vue UI (`/release`)
- [ ] Engine integration (`api.py` bridge to release_tests)
- [ ] Scheduling / Test Plans
- [ ] Docs / chore

## Screenshots (required for UI changes)


## Testing
- [ ] Ran a real **Release Test** against a Testing Site — versions: <!-- develop / v16 / v15 -->
- [ ] Run detail / Test Results render correctly
- [ ] Frontend builds: `cd frontend && yarn build`
- [ ] For DocType changes: fresh install **and** `bench migrate` both succeed

## Safety checklist
- [ ] **No DocType/field renames or removals** without a `patches.txt` migration
- [ ] **No credentials/secrets** committed
- [ ] Compatible with the current `release_tests` engine version
- [ ] Non-destructive on target sites
