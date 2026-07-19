---
phase: 2
slug: investor-profile-feature-engineering-foundation
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-19
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (per `pyproject.toml`'s `[tool.pytest.ini_options]`, established in Phase 1) |
| **Config file** | `pyproject.toml` (`testpaths = ["tests"]`, `pythonpath = ["."]`) |
| **Quick run command** | `pytest tests/test_features_technical.py tests/test_features_leakage.py -x` |
| **Full suite command** | `pytest` (entire `tests/` directory, including the live-local-Supabase-stack tests inherited from Phase 1 — requires `npx supabase start` first, per `tests/conftest.py`'s `supabase_env` fixture) |
| **Estimated runtime** | ~30-45 seconds (full suite, local Supabase stack running) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_features_technical.py tests/test_features_leakage.py -x` (fast, no live-stack dependency)
- **After every plan wave:** Run `pytest` (full suite, requires `npx supabase start`)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | PROFILE-01 | V4/V5 | Profile form saves all scalar fields (risk tolerance, time horizon, sectors, asset types, capital) to Supabase | integration (real local stack, no mocking) | `pytest tests/test_profile_crud.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PROFILE-01 | V4 (IDOR) | Holdings dynamic rows (ticker/quantity/cost-basis) save/read back correctly, RLS-scoped per user | integration (real local stack, two-user isolation) | `pytest tests/test_holdings_rls.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PROFILE-01 | V5 | Invalid/unrecognized ticker on holdings form submit is flagged, not silently saved (D-08; must check `df.empty`, not just exceptions) | unit (mocked `fetch_ohlcv`) | `pytest tests/test_ticker_validation.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PROFILE-02 | V3 | Editing an existing profile and reloading shows updated values immediately (D-13: no `st.cache_data` on profile reads) | integration (real local stack) | `pytest tests/test_profile_crud.py::test_edit_reflects_immediately -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | (infra, supports Phase 3/4) | — | Feature functions (returns/volatility/SMA/RSI) are point-in-time safe — no lookahead | unit + smoke test | `pytest tests/test_features_technical.py tests/test_features_leakage.py -x` | ❌ W0 | ⬜ pending |

*Task ID/Plan/Wave columns are TBD — this file is seeded before planning (plan-phase step 5.5, from RESEARCH.md's Validation Architecture section) and backfilled once PLAN.md files exist, per the Phase 1 precedent.*

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_features_technical.py` — covers each `technical.py` function's basic correctness (known-input/known-output for SMA/RSI/returns/volatility)
- [ ] `tests/test_features_leakage.py` — covers D-11 (truncation-invariance + synthetic-future-signal-injection smoke test)
- [ ] `tests/test_profile_crud.py` — covers PROFILE-01/PROFILE-02 scalar-field save/edit round-trip against the real local Supabase stack
- [ ] `tests/test_holdings_rls.py` — covers holdings RLS isolation (two-user pattern, same shape as Phase 1's `test_rls_policy.py`)
- [ ] `tests/test_ticker_validation.py` — covers D-08 (mocked `fetch_ohlcv`, including the empty-DataFrame invalid-ticker case)
- [ ] New migration: `supabase/migrations/<timestamp>_extend_profiles_and_create_holdings.sql` (plus a same-phase GRANT migration, matching the Phase 1 precedent — do not defer to a follow-up "fix" migration)

---

## Manual-Only Verifications

*None — all phase behaviors have automated verification per the Phase Requirements → Test Map above.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
