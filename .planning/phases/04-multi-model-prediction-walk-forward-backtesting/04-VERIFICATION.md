---
phase: 04-multi-model-prediction-walk-forward-backtesting
verified: 2026-08-17T05:00:00Z
status: human_needed
score: 11/11 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Deploy to Streamlit Community Cloud (or otherwise confirm the deploy build environment) and check that the build log shows a `prophet` wheel install (not a CmdStan source compile step), then time the first Prophet forecast on the deployed app."
    expected: "Prophet imports/fits successfully on the actual Streamlit Cloud Debian build image within a reasonable time, matching the local dev-machine result recorded in 04-05-SUMMARY.md (which required manual CmdStan/RTools installation steps not present in a stock Cloud build)."
    why_human: "04-VALIDATION.md's own 'Manual-Only Verifications' table and 04-05-PLAN.md's purpose section both explicitly flag this as an outstanding empirical deploy-time check outside local pytest's reach — Prophet's cmdstanpy backend can fail independently of the Python import machinery, and this project's local dev-machine Prophet install needed non-trivial manual toolchain fixes (RTools/mingw32-make aliasing) that may or may not apply to Streamlit Cloud's build image."
  - test: "Click 'Compare All Models' on an asset with sufficient history (e.g. AAPL) and observe the interaction end-to-end."
    expected: "An @st.dialog modal opens with the time-cost warning; clicking 'Start Comparison' closes the modal and a persistent yellow st.warning banner appears while all 3 models train sequentially; a st.toast reading 'Model comparison ready.' fires exactly once when done; a 3-column result view appears in sma/xgboost/prophet order."
    why_human: "04-VALIDATION.md's Manual-Only Verifications table explicitly flags this as visual/UX timing behavior across Streamlit's rerun model, not meaningfully assertable via pytest. Code structurally implements all pieces (verified via grep/import checks) but the actual rerun-driven modal-close -> banner-appear -> toast-fire sequence has not been exercised in a running app."
  - test: "Generate a forecast for a high-volatility asset (e.g. a crypto ticker) at the 90-day horizon and visually inspect the resulting chart."
    expected: "The wide confidence-interval band autoscales via Plotly's default y-axis behavior without visually distorting or compressing the historical-price portion of the same chart; the chart remains readable at a narrow (mobile-width) browser viewport."
    why_human: "04-02-PLAN.md and 04-08-PLAN.md both mark this must-have with `verification: backstop` — explicitly deferred to visual/UI-review time, not covered by any automated test. No 04-UI-REVIEW.md exists yet in this phase directory."
  - test: "Trigger the 'Generate Forecast' button for each of the 3 models (SMA, XGBoost, Prophet) and observe the loading state; also trigger the insufficient-history and Prophet-unavailable message states and check text wrapping."
    expected: "SMA feels instant, XGBoost takes a couple seconds, Prophet takes several seconds — all shown via a native st.spinner with no jank or unstyled flash. INSUFFICIENT_HISTORY_MESSAGE and PROPHET_UNAVAILABLE_MESSAGE wrap cleanly inside their st.warning boxes at normal and narrow viewport widths."
    why_human: "04-08-PLAN.md marks both the loading-state and long-text-wrapping must-haves `verification: backstop` — explicitly visual/implementation-time checks, not automated-test-covered."
---

# Phase 04: Multi-Model Prediction + Walk-Forward Backtesting Verification Report

**Phase Goal:** Users can drill into any asset and see multi-model price forecasts with confidence intervals, backed by honest walk-forward-validated accuracy metrics.
**Verified:** 2026-08-17T05:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 (SC1) | User can drill into any recommended or searched asset and see a historical price chart | ✓ VERIFIED | `src/pages/search.py:243` (`render_price_history_chart(result["chart_df"], ...)`) renders unconditionally in both the `insufficient_data` and `scored` branches before `_render_prediction_section` is ever called — unchanged Phase-3 behavior, still present. |
| 2 (SC2) | User can select a prediction model (SMA/XGBoost/Prophet) and a forecast horizon, and generate a forecast | ✓ VERIFIED | `_render_prediction_section` (`search.py:250-341`) renders a `MODEL_LABELS`-driven `st.selectbox` (no default, `index=None`), a `VALID_HORIZONS`-driven horizon `st.selectbox` (7/30/90), and a `Generate Forecast` button gated on both; click invokes `resolve_forecast_request` -> `engine.generate_forecast`, which dispatches to `sma_model`/`xgboost_model`/`prophet_model.forecast_forward` (`src/prediction/engine.py:54-67, 112-144`). |
| 3 (SC3) | The forecast chart displays confidence intervals around the future prediction | ✓ VERIFIED | `build_forecast_figure` (`src/components/charts.py:63-107`) builds a 4-trace figure (historical line + invisible CI-upper + invisible CI-lower with `fill="tonexty"` + dashed forecast line) exactly per spec; wired into `search.py:330-338`'s `render_forecast_chart(...)` call whenever `forecast_result["status"] == "ok"`, immediately followed by `CI_CAPTION`. |
| 4 (SC4) | User can see backtested accuracy (RMSE, directional accuracy, Sharpe) per model, computed via walk-forward validation with no lookahead bias | ✓ VERIFIED | `walk_forward.make_folds` (`src/prediction/walk_forward.py`) routes exclusively through `sklearn.model_selection.TimeSeriesSplit`; `backtest.run_backtest` (`src/prediction/backtest.py:63-141`) slices each fold's fit strictly to `feature_frame.iloc[train_index]`/`price_series.iloc[train_index]`. No-lookahead is structurally proven by `test_folds_never_overlap_and_test_always_after_train`, `test_expanding_window_train_sets_are_supersets`, `test_run_backtest_only_fits_each_fold_on_its_own_train_index_slice`, and `test_perturbation_inside_last_fold_test_window_does_not_leak_into_earlier_fold` (all passing in the 204-test suite). `_render_backtest_metrics_table` (`search.py:344-350`) displays RMSE/Directional Accuracy/"Sharpe Ratio (Simulated)" via `format_metrics_for_display`. |
| 5 | XGBoost's confidence band can never invert (quantile-crossing guard) | ✓ VERIFIED | 04-REVIEW.md's CR-01 (Critical) finding is fixed: `xgboost_model.py:75-77` sorts the three quantile endpoints before returning; regression test `test_fit_predict_sorts_endpoints_when_quantile_regressors_cross` (`tests/test_prediction_xgboost.py:140`) monkeypatches crossing quantiles and asserts the guard holds. |
| 6 | Sharpe-ratio annualization is horizon-aware, not a flat daily-return assumption | ✓ VERIFIED | 04-REVIEW.md's WR-02 fixed: `metrics.sharpe_ratio` now takes `horizon_days` and scales by `periods_per_year / horizon_days` (`src/prediction/metrics.py:40-73`); `test_sharpe_ratio_scales_annualization_by_horizon_days` (`tests/test_prediction_metrics.py:77`) passing. |
| 7 | Search page does not double-fetch the same ticker's OHLCV data (1y + 5y) per render | ✓ VERIFIED | 04-REVIEW.md's WR-01 fixed: `search.py:227-238` fetches 5y once via `fetch_prediction_data`, threads it into `resolve_search_result` (which slices to trailing 1y via `_slice_trailing_year`) and into `_render_prediction_section` — no second live fetch. `mock_fetch_ohlcv.assert_not_called()` regression tests present in `tests/test_universe_loader.py:96` and `tests/test_recommendation_search.py:104,227`. |
| 8 | `HORIZON_LABELS` cannot silently drift from `VALID_HORIZONS` | ✓ VERIFIED | 04-REVIEW.md's WR-03 fixed: `HORIZON_LABELS` centralized in `src/prediction/engine.py:51`; `test_horizon_labels_keys_match_valid_horizons_exactly` (`tests/test_prediction_engine.py:54`) passing. |
| 9 | `run_backtest`'s per-fold return calculation is guarded against zero-division | ✓ VERIFIED | 04-REVIEW.md's WR-04 fixed: `backtest.py:130-133` replaces zero `actual_start` with `NaN` before division and `nan_to_num`s the result; `test_run_backtest_zero_actual_start_does_not_produce_nan_or_inf_metrics` (`tests/test_prediction_backtest.py:165`) passing. |
| 10 | D-06 "Compare All Models" is reachable independent of the single-model flow, degrades gracefully per-model, and never re-sorts the fixed sma/xgboost/prophet order | ✓ VERIFIED | `_render_compare_all_models` call site (`search.py:299`) sits after the `insufficient_data` early-return and before the `model_choice is None` early-return, matching the plan's required placement; loop order follows `MODEL_LABELS`' dict insertion order (`search.py:388,406`); per-model status branching (`prophet_unavailable`/`error`/`ok`) renders independently per column (`search.py:409-415`). |
| 11 | Every v1 requirement ID declared for this phase (PRED-01–04) has a satisfying implementation, and no orphaned requirement exists | ✓ VERIFIED | All 4 IDs appear across the 9 plans' `requirements:` frontmatter (PRED-01: 04-07/04-08; PRED-02: 04-01/04-04/04-05/04-06/04-07/04-08/04-09; PRED-03: 04-02/04-04/04-05/04-06/04-08; PRED-04: 04-03/04-06/04-08/04-09); `.planning/REQUIREMENTS.md` maps only PRED-01–04 to Phase 4, all covered — no orphans. |

**Score:** 11/11 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `requirements.txt` | `xgboost==3.3.0`, `prophet==1.2.1`, `scikit-learn==1.9.0` pinned, 9 pre-existing lines untouched | ✓ VERIFIED | All 3 lines present at end of file; original 9 lines unchanged/unreordered. |
| `src/prediction/__init__.py` | Zero-I/O package marker docstring | ✓ VERIFIED | Docstring explicitly states no `streamlit`/`yfinance`/`sqlite3` import anywhere in the package. |
| `src/components/charts.py` | `build_forecast_figure`/`render_forecast_chart`, `FORECAST_COLOR`/`CI_FILL_COLOR` | ✓ VERIFIED | 4-trace figure, exact colors (`#0EA5E9`, `rgba(14, 165, 233, 0.2)`), reuses `build_price_history_figure`. |
| `src/prediction/walk_forward.py` | `make_folds`, `N_FOLDS=5`, `MIN_PREDICTION_HISTORY_ROWS=750` | ✓ VERIFIED | Routes through `TimeSeriesSplit`; constants match spec with derivation comments. |
| `src/prediction/metrics.py` | `rmse`/`directional_accuracy`/`sharpe_ratio`/`format_metrics_for_display` | ✓ VERIFIED | Asset-class + horizon-aware Sharpe annualization (post-fix), round-half-up display formatting. |
| `src/prediction/sma_model.py` | `forecast_forward`, `Z_80PCT` | ✓ VERIFIED | Random-walk-with-drift + sqrt(time) CI band, zero-variance edge case handled. |
| `src/prediction/xgboost_model.py` | `fit_predict`, `forecast_forward`, `QUANTILES` | ✓ VERIFIED | Direct-horizon quantile regression, endpoint sorting guard (post-fix) for monotonic CI. |
| `src/prediction/prophet_model.py` | `PROPHET_AVAILABLE`, `forecast_forward`, `INTERVAL_WIDTH` | ✓ VERIFIED | Broad `except Exception` import guard; single occurrence of `from prophet import Prophet` in entire codebase. |
| `src/prediction/backtest.py` | `run_backtest`, `MODEL_ENDPOINT_FNS` | ✓ VERIFIED | Fold-index-only slicing, zero-division guard (post-fix), Prophet-unavailable short-circuit before fold work. |
| `src/prediction/engine.py` | `generate_forecast`, `VALID_MODELS`, `VALID_HORIZONS`, `MODEL_LABELS`, `HORIZON_LABELS` | ✓ VERIFIED | Independent input validation before dispatch, exception-safe `{"status": "error"}` fallback, `HORIZON_LABELS` centralized (post-fix). |
| `src/pages/_prediction_loader.py` | `fetch_prediction_data` | ✓ VERIFIED | 5y fetch, `MIN_PREDICTION_HISTORY_ROWS`-gated discriminated-union return, imports (not re-declares) the threshold constant. |
| `src/pages/search.py` | `resolve_forecast_request`, `_render_prediction_section`, `_render_backtest_metrics_table`, `_compare_all_models_dialog`, `_render_compare_all_models` | ✓ VERIFIED | Full D-01–D-08 flow wired end-to-end; page-thin/module-thick discipline maintained (no forecast math computed inline). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `charts.build_forecast_figure` | `charts.build_price_history_figure` | calls it first, adds 3 traces | ✓ WIRED | `charts.py:76` |
| `walk_forward.make_folds` | `sklearn.model_selection.TimeSeriesSplit` | direct call, never hand-rolled loop | ✓ WIRED | `walk_forward.py:43` |
| `backtest.run_backtest` | `walk_forward.make_folds`, `metrics.*`, model `forecast_forward`/`fit_predict` | fold-indexed slicing + shared metrics composition | ✓ WIRED | `backtest.py:32-33, 96-97, 135-140` |
| `engine.generate_forecast` | `backtest.run_backtest`, model `forecast_forward` | single validated dispatch point | ✓ WIRED | `engine.py:122-127` |
| `_prediction_loader.fetch_prediction_data` | `src.data.prices.fetch_ohlcv`, `src.features.feature_frame.assemble_feature_frame`, `walk_forward.MIN_PREDICTION_HISTORY_ROWS` | I/O glue, threshold imported not re-declared | ✓ WIRED | `_prediction_loader.py:22-24, 48, 56-57` |
| `search._render_prediction_section` | `_prediction_loader.fetch_prediction_data`, `engine.generate_forecast` (via `resolve_forecast_request`), `charts.render_forecast_chart` | page calls loader once, engine via cached wrapper, then chart renderer | ✓ WIRED | `search.py:227, 120, 330-337` |
| `search._render_compare_all_models` | `search.resolve_forecast_request` (never `engine.generate_forecast` directly) | sequential 3-model loop reuses the cache boundary | ✓ WIRED | `search.py:389-396` |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PRED-01 | 04-07, 04-08 | Historical price chart on drill-in | ✓ SATISFIED | `search.py:243`, `_prediction_loader.py` |
| PRED-02 | 04-01, 04-04, 04-05, 04-06, 04-07, 04-08, 04-09 | Model + horizon selection, forecast generation | ✓ SATISFIED | `engine.generate_forecast`, `search.py` model/horizon controls |
| PRED-03 | 04-02, 04-04, 04-05, 04-06, 04-08 | Confidence interval display | ✓ SATISFIED | `charts.build_forecast_figure`, cross-model CI invariant test (`test_prediction_ci.py`) |
| PRED-04 | 04-03, 04-06, 04-08, 04-09 | Walk-forward backtested accuracy, no lookahead bias | ✓ SATISFIED | `walk_forward.py`, `backtest.py`, structural + perturbation leakage tests |

No orphaned requirements — `.planning/REQUIREMENTS.md` traces only PRED-01–04 to Phase 4, and all 4 are claimed and satisfied.

### Anti-Patterns Found

None. Scanned `src/prediction/*.py`, `src/pages/_prediction_loader.py`, `src/pages/search.py`, `src/components/charts.py` for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/placeholder/empty-implementation patterns. The only matches were legitimate: `"Prophet is not available in this environment"` (an intentional user-facing runtime message, not a code stub) and Streamlit widget `placeholder=` UI parameters (`SEARCH_INPUT_PLACEHOLDER`, `MODEL_DROPDOWN_PLACEHOLDER`).

### Behavioral Spot-Checks / Test Suite

Full workspace test suite run once (local Supabase Docker stack running, as noted by the requester):

```
pytest tests/ -q
204 passed, 96 warnings in 133.46s
```

This includes every structural no-lookahead-bias test (`test_folds_never_overlap_and_test_always_after_train`, `test_expanding_window_train_sets_are_supersets`, `test_run_backtest_only_fits_each_fold_on_its_own_train_index_slice`, `test_perturbation_inside_last_fold_test_window_does_not_leak_into_earlier_fold`), the cross-model CI-band invariant test (`test_prediction_ci.py`), and all 5 code-review-fix regression tests (`test_fit_predict_sorts_endpoints_when_quantile_regressors_cross`, `test_sharpe_ratio_scales_annualization_by_horizon_days`, `test_horizon_labels_keys_match_valid_horizons_exactly`, `test_run_backtest_zero_actual_start_does_not_produce_nan_or_inf_metrics`, the WR-01 `assert_not_called()` dedup-fetch tests). This independently reproduces the 204-passed figure claimed in 04-REVIEW-FIX.md — the number was not taken on faith from the SUMMARY/REVIEW-FIX report.

### Human Verification Required

4 items — all pre-flagged as manual-only by this phase's own planning artifacts (04-VALIDATION.md's "Manual-Only Verifications" table, and `verification: backstop` must-haves in 04-02-PLAN.md/04-08-PLAN.md). No `04-UI-REVIEW.md` exists yet in this phase directory to close these out.

### 1. Streamlit Community Cloud Prophet deploy validation

**Test:** Deploy to Streamlit Community Cloud (or otherwise confirm the deploy build environment) and check that the build log shows a `prophet` wheel install (not a CmdStan source compile step), then time the first Prophet forecast on the deployed app.
**Expected:** Prophet imports/fits successfully on the actual Cloud Debian build image within a reasonable time.
**Why human:** Explicitly flagged as an outstanding empirical deploy-time check in 04-VALIDATION.md and 04-05-PLAN.md; the local dev-machine Prophet install required non-trivial manual toolchain fixes (RTools/mingw32-make aliasing per 04-05-SUMMARY.md) that may not reflect Cloud's build image.

### 2. Compare All Models end-to-end interaction

**Test:** Click "Compare All Models" on an asset with sufficient history and observe the full modal -> banner -> toast -> results sequence.
**Expected:** Modal opens with time-cost copy; "Start Comparison" closes it and shows a persistent yellow banner during sequential training; a completion toast fires exactly once; a 3-column fixed-order result view appears.
**Why human:** 04-VALIDATION.md flags this as visual/UX timing behavior across Streamlit's rerun model, not assertable via pytest. Code structure is verified (dialog/banner/toast/loop-order all present and grep/test-confirmed) but the live rerun-driven sequence itself is unexercised.

### 3. Wide/narrow-viewport chart rendering

**Test:** Generate a forecast for a high-volatility asset at the 90-day horizon; view at both normal and narrow (mobile) browser widths.
**Expected:** The wide CI band autoscales via Plotly defaults without distorting the historical-price line; chart stays readable narrow.
**Why human:** Explicitly marked `verification: backstop` in 04-02-PLAN.md and 04-08-PLAN.md — visual-only, no automated test exists or was intended.

### 4. Loading-state and message-copy text wrapping

**Test:** Trigger Generate Forecast for each model and observe the spinner; trigger the insufficient-history and Prophet-unavailable states and check message wrapping.
**Expected:** Native `st.spinner` shows cleanly per model's expected latency (SMA instant, XGBoost seconds, Prophet multi-second); warning/error message text wraps cleanly with no truncation.
**Why human:** Explicitly marked `verification: backstop` in 04-08-PLAN.md.

### Gaps Summary

No gaps found. All 11 observable truths (4 roadmap Success Criteria + 5 code-review-fix regressions + 1 D-06 reachability check + 1 requirements-coverage check) are verified in the codebase with passing, independently-reproduced tests (204/204). All 5 findings from 04-REVIEW.md (1 critical, 4 warnings) are confirmed fixed in the actual source, each backed by a dedicated regression test — not just claimed in 04-REVIEW-FIX.md prose. The only open items are 4 pre-flagged manual/visual checks that this phase's own planning artifacts (04-VALIDATION.md, 04-02-PLAN.md, 04-08-PLAN.md) explicitly deferred to human/UI-review time and which have not yet been closed out with a `04-UI-REVIEW.md` or equivalent sign-off.

---

_Verified: 2026-08-17T05:00:00Z_
_Verifier: Claude (gsd-verifier)_
