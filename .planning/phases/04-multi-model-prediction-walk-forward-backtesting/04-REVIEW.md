---
phase: 04-multi-model-prediction-walk-forward-backtesting
reviewed: 2026-08-16T00:00:00Z
depth: standard
files_reviewed: 23
files_reviewed_list:
  - requirements.txt
  - src/components/charts.py
  - src/pages/_prediction_loader.py
  - src/pages/search.py
  - src/prediction/__init__.py
  - src/prediction/backtest.py
  - src/prediction/engine.py
  - src/prediction/metrics.py
  - src/prediction/prophet_model.py
  - src/prediction/sma_model.py
  - src/prediction/walk_forward.py
  - src/prediction/xgboost_model.py
  - tests/_prediction_fixtures.py
  - tests/test_components.py
  - tests/test_prediction_backtest.py
  - tests/test_prediction_ci.py
  - tests/test_prediction_engine.py
  - tests/test_prediction_loader.py
  - tests/test_prediction_metrics.py
  - tests/test_prediction_prophet.py
  - tests/test_prediction_search.py
  - tests/test_prediction_sma.py
  - tests/test_prediction_walk_forward.py
  - tests/test_prediction_xgboost.py
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-08-16T00:00:00Z
**Depth:** standard
**Files Reviewed:** 23
**Status:** issues_found

## Summary

Reviewed the multi-model prediction + walk-forward backtesting package (`src/prediction/`), its I/O loader (`src/pages/_prediction_loader.py`), the search-page prediction UI (`src/pages/search.py`), the shared chart builders (`src/components/charts.py`), and the full accompanying test suite. The walk-forward fold generation (`walk_forward.py`) and its no-lookahead-bias guarantee are solid and well-proven by `tests/test_prediction_backtest.py`'s structural leakage tests. The SMA baseline model is correct by construction (its confidence band can never invert). The XGBoost model, however, has a real correctness gap: its three independently-trained quantile regressors are never checked for monotonicity, so the confidence band it renders to end users can invert in production for real (non-synthetic) price data — this is classified Critical because it directly violates the PRED-03 confidence-interval contract with no code-level or test-level safety net against realistic inputs. Several other issues (redundant network fetches on the search page, a Sharpe-ratio annualization that doesn't account for horizon length, an un-synced label constant, and minor defensive-coding gaps) are flagged as Warnings/Info.

## Critical Issues

### CR-01: XGBoost quantile regressors are not monotonicity-checked — the rendered confidence band can invert

**File:** `src/prediction/xgboost_model.py:50-58, 63-67, 89, 92-96`

**Issue:** `fit_predict` trains three completely independent `XGBRegressor` models at `quantile_alpha` 0.1, 0.5, and 0.9 (lines 50-58), then reads off `ci_lower_endpoint`/`forecast_endpoint`/`ci_upper_endpoint` from their three separate `.predict()` calls (lines 63-67) with no check that `ci_lower_endpoint <= forecast_endpoint <= ci_upper_endpoint`. This is the well-documented "quantile crossing" failure mode of independently-fit quantile regression trees — it is especially likely here because the model is asked to extrapolate to a future horizon endpoint that is very often outside the training distribution's price range (the exact scenario where boosted-tree quantile crossing is most common).

`forecast_forward` (lines 70-96) then computes `endpoint_width = ci_upper_endpoint - ci_lower_endpoint` (line 89) with no `abs()`/clamp, and returns `ci_lower = forecast_path - width_at_t / 2` / `ci_upper = forecast_path + width_at_t / 2` (lines 92-96) unclamped. If the quantiles cross, `endpoint_width` is negative, so the returned `ci_lower` array will be numerically *greater* than `ci_upper` at every step, and `render_forecast_chart` (`src/components/charts.py`) will render an inverted/negative-width shaded band with no downstream validation catching it.

The existing end-to-end invariant test (`tests/test_prediction_ci.py::test_generate_forecast_ci_band_invariant_holds_end_to_end`) asserts `ci_lower[i] <= forecast[i] <= ci_upper[i]` for xgboost, but only against a clean, low-noise synthetic fixture (`tests/_prediction_fixtures.py`'s sinusoidal + linear trend + small Gaussian noise). It would not reliably catch crossing on real, noisier market data (crypto in particular), so this defect can ship undetected.

**Fix:** Enforce monotonicity after prediction, e.g.:
```python
def fit_predict(features: pd.DataFrame, close: pd.Series, horizon_days: int) -> dict:
    ...
    forecast_endpoint = float(models[0.5].predict(latest_row)[0])
    ci_lower_endpoint = float(models[0.1].predict(latest_row)[0])
    ci_upper_endpoint = float(models[0.9].predict(latest_row)[0])

    # Guard against quantile crossing: independently-fit quantile
    # regressors are not guaranteed monotonic, especially when
    # extrapolating beyond the training price range.
    ci_lower_endpoint, forecast_endpoint, ci_upper_endpoint = sorted(
        (ci_lower_endpoint, forecast_endpoint, ci_upper_endpoint)
    )

    return {
        "forecast_endpoint": forecast_endpoint,
        "ci_lower_endpoint": ci_lower_endpoint,
        "ci_upper_endpoint": ci_upper_endpoint,
    }
```
and/or add a regression test that forces crossing (e.g. via a monkeypatched/mocked `XGBRegressor.predict`) to prove the guard holds.

## Warnings

### WR-01: Search page fetches the same ticker's OHLCV data twice per render (1y and 5y), doubling live-fetch/rate-limit exposure

**File:** `src/pages/search.py:149, 232` (see also `src/pages/_universe_loader.py:39` and `src/pages/_prediction_loader.py:48`)

**Issue:** `resolve_search_result` calls `fetch_scorable_row(ticker, ...)` (search.py:149), which internally calls `fetch_ohlcv(ticker)` with the default `period="1y"` (`_universe_loader.py:39`). `_render_prediction_section` is then always invoked afterward and calls `fetch_prediction_data(ticker)` (search.py:232), which internally calls `fetch_ohlcv(ticker, period="5y")` (`_prediction_loader.py:48`). Because `fetch_ohlcv` is `st.cache_data`-keyed on `(ticker, period)`, these are two distinct cache keys, so a single ticker search triggers **two separate live yfinance downloads** for the same ticker on first view (and again after each cache TTL expiry). Given CLAUDE.md explicitly flags yfinance's undocumented rate limits as "the single largest reliability risk in this stack" and mandates minimizing call volume, this doubles the exposure per search unnecessarily — a single 5y fetch could be sliced down to serve both the 1y scoring-chart view and the prediction module.

**Fix:** Either have `resolve_search_result`/`fetch_scorable_row` accept an already-fetched 5y frame and slice the last year for scoring/display, or have `_render_prediction_section` reuse `result["chart_df"]` (already fetched) instead of re-fetching at 5y when the caller already holds sufficient history. At minimum, document why the duplicate fetch is intentional if it is meant to stay.

### WR-02: Sharpe-ratio annualization ignores `horizon_days`, producing magnitudes that are not comparable across the horizon selector

**File:** `src/prediction/metrics.py:40-63`

**Issue:** `sharpe_ratio` treats `captured_returns` (five fold-level returns, each realized over the *selected* `horizon_days`, per `backtest.py:121`) as if they were daily returns, multiplying by `sqrt(TRADING_DAYS_PER_YEAR)` unconditionally. For a 7-day horizon this already dramatically overstates the annualized figure (compounding an already-multi-day return as though it recurred daily); for a 90-day horizon the distortion is even larger and in the opposite relative direction. Since the UI lets users flip between horizons (7/30/90) and expects "apples-to-apples" comparability (per this module's own docstring, "D-06's apples-to-apples 'Compare all models' requirement"), the Sharpe figure is only comparable *across models at a fixed horizon*, not across horizon selections — and its absolute magnitude is not a real annualized Sharpe ratio by any standard definition. This can materially mislead users about a model's risk-adjusted quality despite the "Simulated" label.

**Fix:** Scale the annualization factor by the actual return period, e.g. `periods_per_year / horizon_days` rather than a flat trading-days constant, or drop the "annualized" framing entirely and present the raw per-fold Sharpe with a horizon-qualified label.

### WR-03: `HORIZON_LABELS` in `search.py` is a hand-maintained constant, not derived from/validated against `engine.VALID_HORIZONS`

**File:** `src/pages/search.py:85` (vs. `src/prediction/engine.py:36`)

**Issue:** `search.py` defines `HORIZON_LABELS = {7: "7 Days", 30: "30 Days", 90: "90 Days"}` independently of `engine.VALID_HORIZONS = {7, 30, 90}`. The horizon `st.selectbox` is built from `sorted(VALID_HORIZONS)` (imported from `engine.py`) with `format_func=lambda h: HORIZON_LABELS[h]`. If `VALID_HORIZONS` is ever changed in `engine.py` (e.g. a horizon added/removed) without updating `HORIZON_LABELS` in `search.py`, `format_func` raises an uncaught `KeyError` and crashes the page render. `MODEL_LABELS` is correctly centralized in `engine.py` and imported by `search.py`, but `HORIZON_LABELS` was not given the same treatment, and no test asserts the two sets stay in sync.

**Fix:** Move `HORIZON_LABELS` into `engine.py` alongside `MODEL_LABELS` (single source of truth), or add a test asserting `set(HORIZON_LABELS) == VALID_HORIZONS`.

### WR-04: `run_backtest`'s per-fold return calculation has no zero-division guard, unlike its own `sharpe_ratio` helper

**File:** `src/prediction/backtest.py:119-121`

**Issue:** `captured_returns = predicted_direction * (actual_endpoints / actual_starts - 1)` divides by `actual_starts` (real historical closing prices) with no zero/near-zero guard. `metrics.sharpe_ratio` explicitly guards its own division (`if std == 0: return 0.0`, `metrics.py:61-62`) to avoid `NaN`/`inf`, but the division in `backtest.py` that feeds it has no equivalent protection. While a literal `0` closing price is unlikely for supported asset classes, this is an inconsistency with the codebase's own established defensive-coding convention for financial-value division, and a `0`/near-`0` value (more plausible for some forex pairs' pip-scale values, or bad upstream data) would silently poison the whole backtest with `inf`/`NaN` metrics rather than failing loudly or degrading gracefully.

**Fix:** Add an explicit guard (e.g. skip or clip folds where `actual_start` is ~0) or document why it's considered impossible for this codebase's asset universe.

## Info

### IN-01: `_render_compare_all_models`'s "Compare All Models" button disabled-check is unreachable dead logic

**File:** `src/pages/search.py:346-350`

**Issue:** `compare_clicked = st.button(..., disabled=(prediction_data["status"] != "ok"), ...)`. `_render_compare_all_models` is only ever invoked from `_render_prediction_section` (search.py:269) *after* the `insufficient` branch has already `return`ed (search.py:265-267), and `fetch_prediction_data` only returns `"ok"` or (already-handled) `"insufficient_data"`/`"not_found"`. So by the time this line executes, `prediction_data["status"]` is always `"ok"`, and the `disabled=...` condition is always `False`. Harmless, but it's dead defensive logic that no test or docstring explains, and it should either be removed or accompanied by a comment noting it's a purely defensive belt-and-suspenders guard against future call-site changes.

**Fix:** Add a one-line comment explaining this is a defensive guard for future callers, or remove it since the invariant is already enforced by the caller.

### IN-02: Round-half-up rounding for negative Sharpe values effectively rounds *toward positive infinity*, not away from zero

**File:** `src/prediction/metrics.py:66-73`

**Issue:** `_round_half_up`'s `math.floor(value * factor + 0.5) / factor` is a true "round half up" (toward +infinity) implementation. For non-negative values (`rmse`, `directional_accuracy * 100`) this is indistinguishable from "round half away from zero," but `sharpe` can be negative. At an exact halfway tie, e.g. `-1.245` rounded to 2 decimals: `-1.245 * 100 = -124.5`; `-124.5 + 0.5 = -124.0`; `floor(-124.0) = -124` → displays `-1.24`, whereas the "round half away from zero" behavior a user would likely expect for a negative financial-looking metric would produce `-1.25`. This is a narrow edge case (exact ties only) but worth a one-line docstring caveat since `sharpe` is the one metric here that can be negative.

**Fix:** Either document the toward-+infinity tie-breaking behavior explicitly for negative inputs, or switch to a magnitude-based round-half-away-from-zero implementation if symmetric rounding is desired for `sharpe`.

### IN-03: `run_backtest` raises an undocumented raw `KeyError` for an unrecognized `model_name`, inconsistent with its own documented `RuntimeError` contract

**File:** `src/prediction/backtest.py:96`

**Issue:** `endpoint_fn = MODEL_ENDPOINT_FNS[model_name]` will raise a bare `KeyError` (with no informative message) if `model_name` isn't one of `"sma"`/`"xgboost"`/`"prophet"`. `run_backtest`'s docstring documents only one `Raises:` case (`RuntimeError` for Prophet-unavailable) and doesn't mention this. In practice `generate_forecast` always validates `model` against `VALID_MODELS` before calling `run_backtest`, so this is unreachable via the primary code path today — but `run_backtest` is a public module function reachable directly (as the test suite itself does), and an undocumented, unhelpful `KeyError` is a worse failure mode than a clear `ValueError` with the invalid value in the message.

**Fix:** Validate `model_name` explicitly at the top of `run_backtest` and raise a `ValueError` with an informative message, or document the `KeyError` behavior in the docstring's `Raises:` section.

---

_Reviewed: 2026-08-16T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
