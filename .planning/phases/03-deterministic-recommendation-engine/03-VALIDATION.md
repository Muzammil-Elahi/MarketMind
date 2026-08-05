---
phase: 3
slug: deterministic-recommendation-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-04
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already configured — `pyproject.toml` `[tool.pytest.ini_options]`, `testpaths = ["tests"]`, `pythonpath = ["."]`) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/test_recommendation_*.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_recommendation_*.py -x`
- **After every plan wave:** Run `pytest` (full suite, including existing Phase 1/2 tests — recommendation-engine changes must never break existing auth/profile/feature tests)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | REC-01 | — | Composite score computed with zero network/LLM calls, ranks a synthetic multi-class universe | unit | `pytest tests/test_recommendation_engine.py -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | REC-01 | — | Per-class normalization scoped correctly (no cross-class leakage) | unit | `pytest tests/test_recommendation_factor_scoring.py::test_normalization_is_within_class -x` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 1-2 | REC-02 | — | Composite score object exposes every sub-score/weight independently | unit | `pytest tests/test_recommendation_engine.py::test_score_object_exposes_all_sub_scores -x` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 1-2 | — | — | Cosine similarity correctness; works identically for a brand-new profile with no prior history | unit | `pytest tests/test_recommendation_similarity.py -x` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 2-3 | REC-03 | — | Explanation text derived from the same `sub_scores` dict as the displayed breakdown (no drift) | unit | `pytest tests/test_recommendation_explain.py::test_explanation_traces_to_top_sub_score -x` | ❌ W0 | ⬜ pending |
| 03-04-01 | 04 | 2-3 | REC-04 | T-03-01 | Search path reuses `fetch_ohlcv` (no new yfinance call site); ticker string never interpolated into any query/shell/SQL | unit (mocked `fetch_ohlcv`) | `pytest tests/test_recommendation_search.py -x` | ❌ W0 | ⬜ pending |
| 03-04-02 | 04 | 2-3 | REC-04 | — | Thin-history asset triggers D-08's chart-only/no-score branch instead of rejecting the search | unit | `pytest tests/test_recommendation_search.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_recommendation_engine.py` — stubs for REC-01, REC-02 (composite scoring, sub-score object shape, top-N-per-class grouping)
- [ ] `tests/test_recommendation_factor_scoring.py` — stubs for REC-01 (within-class normalization correctness)
- [ ] `tests/test_recommendation_similarity.py` — stubs for D-02 (cosine similarity correctness, cold-start non-issue framing)
- [ ] `tests/test_recommendation_explain.py` — stubs for REC-03 (template traceability to displayed sub-scores)
- [ ] `tests/test_recommendation_search.py` — stubs for REC-04/D-07/D-08 (mocked `fetch_ohlcv`, thin-history branch)
- [ ] No new framework install needed — pytest already configured

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
