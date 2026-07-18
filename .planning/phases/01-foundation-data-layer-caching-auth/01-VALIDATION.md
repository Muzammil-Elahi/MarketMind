---
phase: 1
slug: foundation-data-layer-caching-auth
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-17
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (none installed yet — greenfield project) |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-XX-XX | TBD | TBD | AUTH-01 | V2/V3 | Signup + login succeeds via Supabase Auth; session persists across reload | integration | `pytest tests/test_auth_flow.py -x` | ❌ W0 | ⬜ pending |
| 01-XX-XX | TBD | TBD | AUTH-02 | V4 | Signed-in user's `profiles` row is written and re-readable in a new session | integration | `pytest tests/test_profile_persistence.py -x` | ❌ W0 | ⬜ pending |
| 01-XX-XX | TBD | TBD | AUTH-03 | V3 | Two concurrent sessions never cross-contaminate `session_state` or any `cache_resource`-wrapped object | integration (`AppTest`) | `pytest tests/test_auth_isolation.py -x` | ❌ W0 | ⬜ pending |
| 01-XX-XX | TBD | TBD | AUTH-03 (RLS) | V4 | A user cannot read/write another user's `profiles` row at the database level | integration (pgTAP or dual-client) | `supabase test db` or `pytest tests/test_rls_policy.py -x` | ❌ W0 | ⬜ pending |
| 01-XX-XX | TBD | TBD | Cache/backoff (success criterion #3) | — | Repeated fetch within TTL hits cache; simulated failure degrades gracefully | unit (mocked yfinance/tenacity) | `pytest tests/test_cache.py -x` | ❌ W0 | ⬜ pending |

*Task IDs and Plan/Wave columns are TBD until the planner assigns concrete plan/task numbers — the planner must fill these in when tasks referencing these requirements are created.*

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `requirements-dev.txt` (or dev extras) — `pytest` install
- [ ] `tests/conftest.py` — shared fixtures: a `mock_supabase_client` fixture for unit-level auth tests, and (if the local CLI route is chosen) a `supabase start`/`stop` session fixture for integration-level RLS tests
- [ ] `pytest.ini` or `pyproject.toml` `[tool.pytest.ini_options]` — test discovery config
- [ ] Decide at planning time: mock Supabase entirely for AUTH-01/02 tests vs. stand up the local Supabase CLI Docker stack for real integration tests (Docker confirmed available on this machine — see RESEARCH.md Environment Availability)

---

## Manual-Only Verifications

*None — all phase behaviors have automated verification per the Phase Requirements → Test Map above.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
