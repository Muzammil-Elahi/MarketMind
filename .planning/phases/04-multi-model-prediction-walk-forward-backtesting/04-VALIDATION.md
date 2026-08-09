---
phase: 4
slug: multi-model-prediction-walk-forward-backtesting
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-09
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already configured — `pyproject.toml` `[tool.pytest.ini_options]`, `testpaths = ["tests"]`, `pythonpath = ["."]`) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/test_prediction_*.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~30-45 seconds (Prophet fits are the slowest tests in the suite per RESEARCH.md Wave 0 Gaps — keep synthetic fixtures at/near the `MIN_PREDICTION_HISTORY_ROWS` floor to bound runtime) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_prediction_*.py -x`
- **After every plan wave:** Run `pytest` (full suite, including existing Phase 1/2/3 tests — prediction-module changes must never break existing auth/profile/feature/recommendation tests)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

Task/Plan/Wave IDs are not yet assigned — this table maps by requirement until `/gsd-plan-phase 4` produces PLAN.md files with real task IDs; the planner/checker should reconcile these rows against actual task IDs once plans exist.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | PRED-01 | — | Historical price chart renders for any resolved ticker (reuses Phase 3's `render_price_history_chart` path) | unit | `pytest tests/test_components.py -x` | ✅ (existing) | ⬜ pending |
| TBD | TBD | TBD | PRED-02 | V5 | Model dropdown + horizon selector + Generate Forecast button produce a forecast for each of the 3 models; `generate_forecast` independently validates `model`/`horizon` against closed enum sets server-side | unit | `pytest tests/test_prediction_sma.py tests/test_prediction_xgboost.py tests/test_prediction_prophet.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PRED-03 | — | Forecast + CI band render correctly (CI widens with horizon; `ci_lower <= forecast <= ci_upper` for every point) | unit | `pytest tests/test_prediction_ci.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PRED-04 | — | Walk-forward backtest produces RMSE/directional accuracy/Sharpe with no lookahead bias (structural split test + D-11-style synthetic-signal-injection smoke test) | unit | `pytest tests/test_prediction_walk_forward.py tests/test_prediction_backtest.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-07/D-08 | — | `_prediction_loader.py`'s `MIN_PREDICTION_HISTORY_ROWS` gate disables model dropdown / Generate Forecast with explanatory message when history is insufficient, chart still renders | unit | `pytest tests/test_prediction_loader.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_prediction_walk_forward.py` — PRED-04 fold-generation correctness (no-overlap, expanding-window superset structural checks; RESEARCH.md Pattern 1 / Pitfall 4)
- [ ] `tests/test_prediction_sma.py` — PRED-02/PRED-03 for the SMA baseline (RESEARCH.md Pattern 2)
- [ ] `tests/test_prediction_xgboost.py` — PRED-02/PRED-03 for XGBoost (RESEARCH.md Pattern 3); use small synthetic fixtures (≤750 rows) to keep training time bounded
- [ ] `tests/test_prediction_prophet.py` — PRED-02/PRED-03 for Prophet (RESEARCH.md Pattern 4); expect the slowest tests in the suite — keep synthetic fixtures minimal, prefer one real-fit integration test plus mocked-fit tests for orchestration logic
- [ ] `tests/test_prediction_backtest.py` — PRED-04's D-11-style leakage smoke test + asset-class-aware Sharpe (RESEARCH.md Pitfall 5)
- [ ] `tests/test_prediction_loader.py` — `MIN_PREDICTION_HISTORY_ROWS` gate (D-07/D-08), mirroring `tests/test_universe_loader.py`'s existing shape
- [ ] Framework install: none needed — `pytest` already configured; only the three new production dependencies (`xgboost`/`prophet`/`scikit-learn`) need installing (behind the Package Legitimacy `checkpoint:human-verify` gate per RESEARCH.md)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Prophet import/fit succeeds on the actual Streamlit Community Cloud build environment (not just local dev) | PRED-02 | STATE.md explicitly flags this as needing empirical validation, not just documentation research — cannot be proven by a local pytest run alone | Deploy with `prophet==1.2.1` installed, check the build log shows a wheel install (not a CmdStan compile step), and time the first `Prophet().fit()` call in the deployed app |
| D-06 "Compare all models" shows both the modal popup AND the persistent yellow banner, and a completion toast on finish | PRED-02/PRED-03 | Visual/UX timing behavior across Streamlit's rerun model — not meaningfully assertable via pytest | Click "Compare all models" on an asset with sufficient history; confirm modal + persistent `st.warning` banner both appear, and `st.toast` fires when all 3 models finish |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
