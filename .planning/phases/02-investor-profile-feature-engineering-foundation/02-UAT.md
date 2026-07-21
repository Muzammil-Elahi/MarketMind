---
status: testing
phase: 02-investor-profile-feature-engineering-foundation
source: [02-VERIFICATION.md]
started: 2026-07-20T22:35:00Z
updated: 2026-07-20T22:35:00Z
---

## Current Test

number: 1
name: PROFILE-02 end-to-end save/reload walkthrough
expected: |
  Run `streamlit run src/app.py` with the local Supabase stack up. Log in with an existing test account.
  Confirm "Investor Profile" appears in nav only after login. Fill every scalar field, add two holdings
  rows (one valid ticker like AAPL, one invalid like ZZZZZZINVALID), click Save. Confirm the invalid-ticker
  error + red-border highlight appear and nothing was saved (reload — fields at prior state). Fix the
  ticker, save again; confirm "Profile saved." appears, page reloads with just-saved values pre-filled.
  Reload again (fresh visit) and confirm the same values persist. Remove a holdings row, save, confirm
  it's gone after reload.
awaiting: user response

## Tests

### 1. PROFILE-02 end-to-end save/reload walkthrough
expected: Every step behaves as described above — this is PROFILE-02's actual "no stale cache" success criterion.
result: [pending]

### 2. CR-01 fix confirmation — missing-quantity row must not delete existing holdings
expected: |
  As a signed-in user with previously-saved holdings, add a new holdings row with only a ticker filled
  in (leave quantity blank), click Save Profile. An error `Quantity is required for "{ticker}".` appears
  with the red-border highlight; nothing is saved; reloading the page shows all pre-existing holdings
  still present.
result: [pending]

### 3. WR-01 fix confirmation — unsaved scalar-field edits survive a validation-failure rerun
expected: |
  Change risk tolerance, time horizon, and capital to new values, then also add an invalid-ticker holdings
  row, and click Save Profile (triggering the invalid-ticker rejection path). The error appears and nothing
  saves, but the risk tolerance/time horizon/capital fields you just changed remain showing your new
  (unsaved) selections — not reset to the prior DB-persisted values.
result: [pending]

### 4. Minor visual/UX backstop items
expected: |
  - Profile and holdings reads on page load are near-instant with no custom skeleton/spinner.
  - A holdings ticker cell with an unusually long or malformed entry displays acceptably.
  - Concurrent edits to the same profile from two browser tabs are not merged/conflict-checked
    (last-write-wins) — explicitly accepted as out of scope for v1, informational only.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
