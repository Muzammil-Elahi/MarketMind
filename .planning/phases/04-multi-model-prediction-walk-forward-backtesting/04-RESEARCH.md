# Phase 4: Multi-Model Prediction + Walk-Forward Backtesting - Research

**Researched:** 2026-08-09
**Domain:** Multi-model time-series price forecasting (naive baseline, gradient-boosted trees, additive-regression), confidence-interval estimation, walk-forward (rolling-origin) backtesting with no-lookahead-bias guarantees, Streamlit Community Cloud build-environment risk for a compiled-dependency package (Prophet/cmdstanpy)
**Confidence:** MEDIUM-HIGH (core techniques — `TimeSeriesSplit`-based walk-forward validation, XGBoost quantile regression, Prophet's native confidence intervals — are standard, well-documented patterns confirmed via official docs/registry; the Prophet/cmdstanpy Streamlit Cloud cold-start risk and the exact minimum-history/fold-count scheme are synthesized recommendations, tagged `[ASSUMED]` where genuine design freedom exists)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Model selection UX**
- **D-01:** Model picker is a dropdown — one model (SMA baseline / XGBoost / Prophet) shown at a time, not tabs and not a permanent side-by-side layout. Switching models re-renders the same forecast+backtest layout.
- **D-02:** No model is pre-selected by default. The drill-in page shows only the historical price chart until the user explicitly picks a model.

**Forecast horizon & generation trigger**
- **D-03:** Forecast horizon is a fixed preset selector: 7 / 30 / 90 days — not a free slider, not a single hardcoded horizon.
- **D-04:** Generating a forecast is an explicit action (a "Generate Forecast" button), not automatic on model/horizon change. Rationale: avoids surprising the user with a multi-second XGBoost/Prophet training delay on every dropdown change — especially relevant given Prophet's cmdstanpy cold-start risk already flagged in STATE.md as needing empirical validation this phase.

**Backtest accuracy display**
- **D-05:** Backtested accuracy (RMSE, directional accuracy, Sharpe) renders as a metrics table below the forecast chart, for the currently selected model — mirrors Phase 3's Score Breakdown pattern (`components/charts.py`'s `render_breakdown_bar_chart`) for UI consistency.
- **D-06:** The default view shows metrics for the selected model only, but there is a separate **"Compare all models"** action the user can trigger to see all 3 models' backtest metrics side-by-side. Because this may require training/backtesting models not yet computed for this asset, the UI must show, together: (a) a popup/modal when the user selects "Compare all models", and (b) a persistent yellow warning banner on the page — both stating the comparison may take time. When the comparison finishes, show a completion notification (toast/success banner — Streamlit has no true push notifications, so this is the closest equivalent; exact widget is Claude's discretion).

**Insufficient-data handling**
- **D-07:** Prediction/backtesting needs its own minimum-history threshold, stricter than Phase 3's `MIN_HISTORY_ROWS` (20) — enough real history to run several walk-forward train/test folds, not just compute one point-in-time feature row. Exact value is Claude's discretion at planning/research time, but it must be visibly larger than 20 and justified against the walk-forward fold count/window chosen.
- **D-08:** When an asset has enough history for the price chart but not enough for a reliable backtest, the price chart still renders (same non-blocking precedent as Phase 3's D-08 for scoring) but the model dropdown / "Generate Forecast" button is disabled with an explanatory message (e.g. "Not enough price history to generate a reliable forecast for this asset.").

### Claude's Discretion

- Exact minimum-history threshold value for D-07 and the walk-forward fold/window scheme it must support. **Resolved below: `MIN_PREDICTION_HISTORY_ROWS = 750`** (see Common Pitfalls / Pitfall 2 and Code Examples).
- Exact widget/mechanism for the D-06 completion notification (Streamlit `st.toast`, `st.success`, or similar). **Resolved below: `st.toast()`** (see Architecture Patterns, Pattern 5).
- Whether the new prediction code lives in `src/prediction/` as its own package (mirroring `src/recommendation/`'s zero-I/O-except-chokepoints structure) — strongly implied by the existing architecture but not explicitly discussed. **Resolved below: yes, `src/prediction/` zero-I/O package + a new `src/pages/_prediction_loader.py` I/O loader**, mirroring the Phase 3 `src/recommendation/` + `src/pages/_universe_loader.py` split exactly.

### Deferred Ideas (OUT OF SCOPE)

None raised during this discussion — session stayed within phase scope. Explicitly out of this phase per the phase boundary: LLM reranking/annotation (Phase 5), news-sentiment features (v2 SENT-01), additional models beyond SMA/XGBoost/Prophet (v2 MODEL-01), recommendation scoring changes (Phase 3, already shipped), any portfolio-level optimizer (explicitly out of project scope per REQUIREMENTS.md).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PRED-01 | User can drill into any asset (recommended or searched) and see a historical price chart | Reuses `src/pages/search.py` + `build_price_history_figure` unchanged (Architectural Responsibility Map, Reusable Assets) |
| PRED-02 | User can select a prediction model (SMA baseline, XGBoost, or Prophet) and a forecast horizon, and generate a forecast | Standard Stack, Architecture Patterns (Pattern 1-4: SMA/XGBoost/Prophet model modules + `engine.py` orchestrator), Code Examples |
| PRED-03 | The forecast chart displays confidence intervals around the future prediction | Architecture Patterns Pattern 3 (per-model CI computation), Pattern 6 (Plotly CI band), Code Examples |
| PRED-04 | User can see backtested accuracy per model (RMSE, directional accuracy, Sharpe), computed via walk-forward validation with no lookahead bias | Architecture Patterns Pattern 1 (`TimeSeriesSplit`-based walk-forward split), Common Pitfalls (Pitfall 1, 4), Code Examples (leakage smoke test) |
</phase_requirements>

## Summary

This phase adds a new zero-I/O `src/prediction/` package (mirroring Phase 3's `src/recommendation/` package) that consumes the existing `fetch_ohlcv`/`assemble_feature_frame` chokepoints and produces three interchangeable forecast+backtest pipelines — a naive SMA/random-walk-with-drift baseline, an XGBoost direct-horizon quantile regressor, and a Prophet additive-regression model — behind one shared `TimeSeriesSplit`-based walk-forward validator. The single biggest structural finding is that **no model in this phase can share Phase 3's 1-year default fetch window or 20-row minimum-history gate**: walk-forward validation with up to 5 expanding-window folds and a worst-case 90-day test window needs a substantially longer history, so this phase must call `fetch_ohlcv(ticker, period="5y")` (a new call site — the chokepoint's signature already supports this via its existing `period` parameter, no chokepoint change required) and gate on a new, much stricter `MIN_PREDICTION_HISTORY_ROWS = 750`.

The second major finding resolves STATE.md's flagged Prophet/cmdstanpy concern with more nuance than "it might not build": since Prophet 1.1, PyPI ships prebuilt `manylinux` x86_64 wheels with a **precompiled CmdStan binary already bundled inside the wheel** (pruned to ~20MB), so a normal `pip install prophet` on Streamlit Community Cloud's Debian/x86_64 build image should not need to compile C++ or reach GitHub at build or runtime — this is a materially lower risk than a from-source CmdStan build. However, an unresolved Streamlit Community forum thread documents CmdStanPy's install-time GitHub-download fallback failing with no working fix, so **empirical validation of the actual deployed build (not just this research) remains mandatory**, exactly as STATE.md requires, and the plan must include a runtime fallback (disable the Prophet option in the UI, matching the D-08 non-blocking pattern) if `import prophet` fails.

The third major finding is per-model confidence-interval computation: Prophet has this built in (`interval_width`); XGBoost gets it "for free" on CPU via the native `reg:quantileerror` objective (XGBoost ≥ 2.0, already satisfied by the pinned `3.3.0`) trained at low/high quantiles; the SMA baseline gets it via the standard random-walk "square-root-of-time" heuristic (`± z · σ(daily returns) · √t`) — no extra dependency needed for any of the three, keeping this phase within the `$0`/CPU-only constraint.

**Primary recommendation:** Build `src/prediction/{walk_forward.py, sma_model.py, xgboost_model.py, prophet_model.py, metrics.py, backtest.py, engine.py}` as pure pandas/numpy(/xgboost/prophet) functions with zero I/O, fed by a new `src/pages/_prediction_loader.py` (mirrors `_universe_loader.py`) that fetches 5 years of history and gates on `MIN_PREDICTION_HISTORY_ROWS`. Extend `src/pages/search.py` with the D-01/D-02/D-03/D-04 model/horizon/Generate-Forecast controls and a D-06 "Compare all models" action using `st.dialog` (modal) + a persistent `st.session_state`-driven yellow `st.warning` banner + `st.toast` (completion notification). Add `build_forecast_figure` to `src/components/charts.py` using Plotly's standard `fill='tonexty'` shaded-band pattern, following the existing pure-builder/thin-renderer split.

## Architectural Responsibility Map

This project is a layered pipeline within one Streamlit process (per Phase 3's established framing) — "tiers" map to Python module boundaries, not deployable services.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 5-year OHLCV fetch for prediction | Data Layer (`src/data/cache.py` → `fetch_ohlcv(ticker, period="5y")`) | — | Reuses the existing chokepoint verbatim with a longer `period` argument; no new fetch path, no chokepoint signature change |
| Point-in-time feature assembly | Feature Layer (`src/features/feature_frame.py` → `assemble_feature_frame`) | — | Already-established chokepoint from Phase 2; prediction code must consume, never reimplement rolling-window logic |
| Minimum-history gate (D-07/D-08) | Data Layer (`src/pages/_prediction_loader.py`, new — I/O, so lives under `src/pages/` per the existing `_universe_loader.py` precedent) | — | Same reasoning as `_universe_loader.py`: performs I/O, so it cannot live in the zero-I/O `src/prediction/` package |
| Walk-forward split generation (PRED-04) | Application/Domain Logic (`src/prediction/walk_forward.py`) | — | Pure function of (n_rows, n_folds, test_size) → list of (train_idx, test_idx) tuples; no I/O, no model-specific logic |
| SMA baseline forecast + CI | Application/Domain Logic (`src/prediction/sma_model.py`) | — | Pure transform of an already-fetched price series; no I/O |
| XGBoost forecast + CI | Application/Domain Logic (`src/prediction/xgboost_model.py`) | Feature Layer (`assemble_feature_frame`) | Pure transform of an already-computed feature frame; trains in-process, no persisted model artifact needed for v1 |
| Prophet forecast + CI | Application/Domain Logic (`src/prediction/prophet_model.py`) | — | Pure transform; the only module where import itself can fail (cmdstanpy backend) — must be import-guarded so one bad import doesn't crash the whole `src/prediction/` package |
| Backtest metrics (RMSE/directional accuracy/Sharpe) | Application/Domain Logic (`src/prediction/metrics.py` + `backtest.py`) | — | Pure aggregation over walk-forward fold predictions vs. actuals; Sharpe's annualization factor depends on `asset_class` (already known from `src/recommendation/universe.py`), so it is passed in, never re-derived from the ticker string |
| Forecast/backtest orchestration (D-01–D-06) | Application/Domain Logic (`src/prediction/engine.py`) | — | Single `generate_forecast(ticker, model, horizon, feature_frame, price_df, asset_class)` entry point mirroring `src/recommendation/engine.py`'s `score_universe` role — one orchestrator, never duplicated per page |
| Forecast chart with CI band (PRED-03) | Frontend Server (`src/components/charts.py` → new `build_forecast_figure`/`render_forecast_chart`) | Browser/Client (Plotly interactivity only) | Extends the existing pure-builder/thin-renderer split (`build_price_history_figure` precedent) |
| Model/horizon controls, Generate Forecast, Compare-all-models modal/banner/toast | Frontend Server (`src/pages/search.py`, extended) | Browser/Client (widget interactivity, `st.dialog`) | Page orchestrates calls into `src/prediction/engine.py` and renders results; owns no forecast/backtest math itself (mirrors Phase 3's page-thin/module-thick split) |
| `require_auth()` gate | Frontend Server (unchanged, already on `search.py`) | — | No new auth surface this phase |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| xgboost | 3.3.0 (per `CLAUDE.md`; `3.4.0` is current latest on PyPI) | Direct-horizon gradient-boosted price/quantile regression | Industry-standard tabular model; native `reg:quantileerror` objective (available since 2.0, satisfied by 3.3.0) gives free CPU-only prediction intervals with no extra dependency `[VERIFIED: pip index versions xgboost → 3.3.0 present, latest 3.4.0]` |
| prophet | 1.2.1 (per `CLAUDE.md`; `1.3.0` is current latest on PyPI) | Time-series forecast with built-in trend/seasonality decomposition + native confidence intervals | Purpose-built for exactly this phase's "forecast + CI + backtest" pattern; since 1.1 ships prebuilt manylinux/win_amd64 wheels with CmdStan bundled, removing most of the historical PyStan/compile pain `[VERIFIED: pip index versions prophet → 1.2.1 present, latest 1.3.0; pip install --dry-run prophet==1.2.1 resolves cleanly with no compile step even on Python 3.13]` |
| scikit-learn | 1.9.0 (per `CLAUDE.md`, matches current PyPI latest) | `TimeSeriesSplit` for walk-forward folds; `mean_squared_error`/directional-accuracy helper utilities | `sklearn.model_selection.TimeSeriesSplit(n_splits, test_size, gap)` is the standard, already-audited implementation of expanding-window walk-forward validation — reusing it instead of hand-rolling fold-index arithmetic directly satisfies PRED-04's no-lookahead-bias requirement `[VERIFIED: pip index versions scikit-learn → 1.9.0 is both the pinned and the current latest]` |
| pandas / numpy | 2.3.3 / 2.3.4 (already pinned, Phase 2/3) | DataFrame slicing per fold, residual/quantile arithmetic | Already the project's data backbone; no new pinning needed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| cmdstanpy | pulled in transitively by `prophet` (currently resolves to `1.3.0`) | Prophet's Stan backend | Never imported directly by this codebase's code — only `prophet` should be imported; `cmdstanpy` stays an indirect (transitive) dependency, not a `requirements.txt` line item, matching `CLAUDE.md`'s "auto-installed dep" framing |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `sklearn.model_selection.TimeSeriesSplit` for walk-forward folds | Hand-rolled fold-index loop | Explicitly rejected — see Don't Hand-Roll below. `TimeSeriesSplit` is a two-line, already-tested call; a hand-rolled loop is exactly the kind of off-by-one-prone code that causes silent lookahead bias. |
| XGBoost `reg:quantileerror` for CI | `scikit-learn`'s `GradientBoostingRegressor(loss="quantile")` | `scikit-learn`'s quantile GBM is a valid fallback if `xgboost`'s quantile objective proves flaky in practice during Phase 4 execution, but since `xgboost` is already a required v1 model per `CLAUDE.md`, using its native quantile support avoids a second gradient-boosting implementation for the same model family. |
| SMA-baseline "square-root-of-time" Gaussian CI | Bootstrap resampling of historical residuals | Bootstrap is more distribution-free (no normality assumption) but adds compute cost (hundreds of resamples) for a baseline model that is supposed to be the cheapest of the three — the Gaussian heuristic is the standard, textbook random-walk CI and is the appropriate complexity level for a "baseline" model. Document as `[ASSUMED]` (see Assumptions Log) since CONTEXT.md leaves this open. |
| Direct-to-horizon-endpoint XGBoost regression (one model per Generate-Forecast click) | Recursive one-step-ahead XGBoost forecasting, walked forward 90 times | Recursive forecasting compounds tree-model error over up to 90 steps and trees do not extrapolate outside their training distribution — a well-documented failure mode. The "direct" multi-step strategy (train the model on a target shifted by exactly the selected horizon) eliminates error compounding entirely, at the cost of a full retrain per horizon selection — acceptable here since D-04 already requires an explicit "Generate Forecast" click per horizon, not a continuous slider. `[CITED: multi-step forecasting strategy comparison, MachineLearningMastery.com / xgboosting.com — direct vs. recursive tradeoff]` |

**Installation:**
```bash
# CLAUDE.md's Recommended Stack already specifies these three lines for
# requirements.txt; none are present yet (confirmed by reading
# requirements.txt directly — 260809 state has streamlit/supabase/
# yfinance/tenacity/python-dotenv/pandas-ta-classic/pandas/numpy/plotly
# only, no ML libraries).
echo "xgboost==3.3.0" >> requirements.txt
echo "prophet==1.2.1" >> requirements.txt
echo "scikit-learn==1.9.0" >> requirements.txt
```

**Version verification:** All three versions confirmed present and installable via `pip index versions <pkg>` against the live PyPI index on the research date (2026-08-09): `xgboost` 3.3.0 exists (latest 3.4.0), `prophet` 1.2.1 exists (latest 1.3.0), `scikit-learn` 1.9.0 exists and **is** the current latest `[VERIFIED: pip index versions]`. A `pip install --dry-run` of all three against this machine's Python 3.13 environment resolved cleanly with prebuilt wheels for every dependency (including `cmdstanpy`) and **no compilation step was triggered** `[VERIFIED: pip install --dry-run, this session]` — this is a positive signal for wheel availability generally, though it was run on Windows/amd64, not Streamlit Cloud's Debian/Linux/amd64 build image, so it does not by itself prove the Linux manylinux wheel path (see Common Pitfalls, Pitfall 1). `CLAUDE.md`'s own guidance to target Python 3.11/3.12 (not 3.13/3.14) for Streamlit Cloud remains the safer, more conservative choice and should stand — this dry-run only reduces confidence that 3.13 is a hard blocker, it does not change the recommendation.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| xgboost | PyPI | Foundational ML library (est. 2014); explicitly named in `CLAUDE.md`'s Recommended Stack with detailed version-compatibility reasoning | Not resolvable via the legitimacy tool's PyPI signal set (`weeklyDownloads: null`) | Not resolvable via the tool's signal set (`repoUrl: null`) | `SUS` (tool flag: `too-new`, `unknown-downloads`, `no-repository`) | **Approved** — see override note |
| prophet | PyPI | Facebook/Meta-maintained forecasting library (est. 2017); explicitly named in `CLAUDE.md` | Not resolvable via the tool's PyPI signal set | `https://facebook.github.io/prophet/` (resolved) | `SUS` (tool flag: `unknown-downloads`) | **Approved** — see override note |
| scikit-learn | PyPI | Foundational ML library (est. 2007); explicitly named in `CLAUDE.md` | Not resolvable via the tool's PyPI signal set | Not resolvable via the tool's signal set | `SUS` (tool flag: `unknown-downloads`, `no-repository`) | **Approved** — see override note |
| cmdstanpy | PyPI | Official Stan Development Team package (est. 2019), transitive dep of `prophet` | Not resolvable via the tool's PyPI signal set | `https://github.com/stan-dev/cmdstanpy` (resolved) | `SUS` (tool flag: `unknown-downloads`) | **Approved** — see override note; not a direct `requirements.txt` entry |

**Tool-verdict override note:** `gsd-tools query package-legitimacy check --ecosystem pypi xgboost prophet scikit-learn cmdstanpy` returned `SUS` for all four, driven entirely by the tool's PyPI metadata source not resolving weekly-download counts (and, for `xgboost`/`scikit-learn`, not resolving a repo URL either) — the exact same known tool limitation documented in `03-RESEARCH.md`'s `numpy` override (not a genuine legitimacy concern). All four are foundational, long-established, widely-used packages already named with explicit version-compatibility reasoning in `CLAUDE.md`. The one flag worth taking seriously on its own merits is `xgboost`'s `too-new` reason — this reflects the tool checking the *latest* PyPI release timestamp (`2026-08-04`, i.e. `3.4.0`, five days before this research), not the pinned `3.3.0` (`2025`-era release); pinning to `3.3.0` specifically (already `CLAUDE.md`'s stated choice) avoids relying on a release that is only days old.

Per the package-legitimacy protocol, the planner should add one `checkpoint:human-verify` step before pinning all three direct dependencies in `requirements.txt` (a single combined checkpoint, mirroring Phase 3's `numpy`/`plotly` precedent in `03-03-PLAN.md`), not a per-package gate.

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** `xgboost`, `prophet`, `scikit-learn`, `cmdstanpy` — all tool-metadata-gap false positives, not real risk signals (see override note above).

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ src/pages/search.py (extended, require_auth()-gated)                 │
│                                                                        │
│  [ticker search — unchanged from Phase 3]                             │
│         │                                                             │
│         ▼                                                             │
│  render_price_history_chart(chart_df)   ← always renders (D-02/PRED-01)│
│         │                                                             │
│         ▼                                                             │
│  model = st.selectbox([None, "SMA", "XGBoost", "Prophet"])  (D-01/D-02)│
│  horizon = st.selectbox([7, 30, 90])                          (D-03) │
│         │                                                             │
│         ▼                                                             │
│  [disabled if rows < MIN_PREDICTION_HISTORY_ROWS]              (D-08)│
│  st.button("Generate Forecast")                                (D-04)│
│         │ on click                                                    │
│         ▼                                                             │
│  src.prediction.engine.generate_forecast(ticker, model, horizon, ...) │
└─────────┬───────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│ src/prediction/engine.py  (zero I/O)                                  │
│                                                                        │
│  1. walk_forward.make_folds(n_rows, n_splits=5, test_size=horizon)    │
│  2. dispatch to sma_model / xgboost_model / prophet_model:            │
│       for each fold: fit(train slice) → predict(test slice)           │
│       → out-of-fold predictions + actuals                             │
│  3. metrics.compute_backtest_metrics(preds, actuals, asset_class)     │
│       → {rmse, directional_accuracy, sharpe}                          │
│  4. <model>.forecast_forward(full_history, horizon)                   │
│       → {forecast_path, ci_lower, ci_upper}                           │
│  5. return {forecast, ci, backtest_metrics}                           │
└─────────┬───────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│ src/components/charts.py                                              │
│  build_forecast_figure(price_df, forecast_df, ci_lower, ci_upper)     │
│  render_forecast_chart(...)  → st.plotly_chart                        │
│  render_breakdown_bar_chart-style metrics table for backtest_metrics  │
└─────────────────────────────────────────────────────────────────────┘

  D-06 "Compare all models" side path:
  st.button("Compare all models")
    → st.session_state["comparing"] = True  (drives persistent yellow st.warning banner)
    → @st.dialog("Comparing all models") popup, same warning text
    → sequentially calls engine.generate_forecast for the 2 uncomputed models
    → st.toast("Comparison ready") on completion
    → st.session_state["comparing"] = False
```

### Recommended Project Structure
```
src/prediction/
├── __init__.py
├── walk_forward.py     # TimeSeriesSplit-based fold generator (PRED-04)
├── sma_model.py         # random-walk-with-drift baseline: forecast + sqrt-time CI
├── xgboost_model.py     # direct-horizon quantile regressors: forecast + CI
├── prophet_model.py     # Prophet wrapper: forecast + native CI, import-guarded
├── metrics.py           # RMSE, directional accuracy, asset-class-aware Sharpe
├── backtest.py          # orchestrates walk_forward + per-model predict → metrics
└── engine.py            # generate_forecast(ticker, model, horizon, ...) orchestrator

src/pages/
├── _prediction_loader.py   # NEW — I/O: fetch_ohlcv(period="5y") + assemble_feature_frame
│                            #        + MIN_PREDICTION_HISTORY_ROWS gate (mirrors
│                            #        _universe_loader.py's fetch_scorable_row shape)
└── search.py                # extended with model/horizon controls, Generate Forecast,
                              # Compare-all-models dialog/banner/toast

src/components/
└── charts.py                # + build_forecast_figure / render_forecast_chart
```

### Pattern 1: Walk-forward folds via `TimeSeriesSplit` (PRED-04, no lookahead)
**What:** Generate `n_splits` expanding-window (train, test) index pairs over the already-fetched, already-dropna'd feature/price frame, where every test fold is strictly after its train fold and every train fold is a superset of the previous one.
**When to use:** Every backtest run, for every model — this is the single shared split function all three models use, so no model can implement its own (potentially leaky) splitting logic.
**Example:**
```python
# src/prediction/walk_forward.py
# Source: scikit-learn official docs (sklearn.model_selection.TimeSeriesSplit)
from sklearn.model_selection import TimeSeriesSplit

N_FOLDS = 5


def make_folds(n_rows: int, horizon_days: int, n_folds: int = N_FOLDS):
    """Return a list of (train_index, test_index) numpy-array pairs.

    Expanding-window: train_index for fold k is always a superset of fold
    k-1's train_index. test_index is always strictly after max(train_index)
    for its fold -- this is the structural guarantee against lookahead bias
    (PRED-04). test_size == horizon_days so backtest folds match the
    forecast horizon the user actually selected.
    """
    splitter = TimeSeriesSplit(n_splits=n_folds, test_size=horizon_days)
    return list(splitter.split(range(n_rows)))
```

### Pattern 2: SMA baseline — random walk with drift + square-root-of-time CI
**What:** The textbook "naive" forecasting baseline: tomorrow's price = today's price + average historical daily return; the CI widens with `sqrt(horizon)` because a random walk's variance grows linearly with time.
**When to use:** The "SMA baseline" model option (D-01). Also the reference point every other model's backtest metrics should beat.
**Example:**
```python
# src/prediction/sma_model.py
# Source: standard random-walk-with-drift forecasting formula (textbook time
# series pattern, e.g. Hyndman & Athanasopoulos "Forecasting: Principles and
# Practice", ch. "Drift method")
import numpy as np
import pandas as pd

Z_80PCT = 1.2816  # two-sided 80% CI z-score, matches Prophet's default interval_width


def forecast_forward(close: pd.Series, horizon_days: int) -> dict:
    daily_returns = close.pct_change().dropna()
    drift = daily_returns.mean()
    sigma = daily_returns.std()

    last_price = close.iloc[-1]
    days = np.arange(1, horizon_days + 1)
    path = last_price * (1 + drift) ** days
    # sqrt(time) scaling: variance of a sum of i.i.d. daily returns grows
    # linearly with the number of days, so std grows with sqrt(days).
    band = last_price * sigma * np.sqrt(days) * Z_80PCT

    return {
        "forecast": path,
        "ci_lower": path - band,
        "ci_upper": path + band,
    }
```

### Pattern 3: XGBoost direct-horizon quantile regression
**What:** Train three `XGBRegressor` models (quantiles 0.1 / 0.5 / 0.9) on a target column shifted `horizon_days` into the future — a "direct" multi-step strategy, not recursive — using the existing `assemble_feature_frame` output as `X`.
**When to use:** The "XGBoost" model option. Trained fresh per Generate-Forecast click (D-04 already gates this behind an explicit action, so a full retrain per horizon selection is acceptable cost).
**Example:**
```python
# src/prediction/xgboost_model.py
# Source: XGBoost official docs, Quantile Regression example
# (https://xgboost.readthedocs.io/en/stable/python/examples/quantile_regression.html)
import numpy as np
import pandas as pd
from xgboost import XGBRegressor

QUANTILES = [0.1, 0.5, 0.9]


def _make_direct_target(close: pd.Series, horizon_days: int) -> pd.Series:
    """Target = close price horizon_days in the future. Rows near the end
    of history have no valid target and must be dropped before training
    (they are exactly the rows the live forward forecast predicts for)."""
    return close.shift(-horizon_days)


def fit_predict(features: pd.DataFrame, close: pd.Series, horizon_days: int):
    target = _make_direct_target(close, horizon_days)
    train_mask = target.notna()
    X_train, y_train = features.loc[train_mask], target.loc[train_mask]

    models = {}
    for q in QUANTILES:
        model = XGBRegressor(
            objective="reg:quantileerror",
            quantile_alpha=q,
            tree_method="hist",
            n_estimators=200,
        )
        model.fit(X_train, y_train)
        models[q] = model

    # Live forward forecast: predict off the most recent feature row (no
    # target exists for it yet -- that's the point).
    latest_row = features.iloc[[-1]]
    return {
        "forecast_endpoint": models[0.5].predict(latest_row)[0],
        "ci_lower_endpoint": models[0.1].predict(latest_row)[0],
        "ci_upper_endpoint": models[0.9].predict(latest_row)[0],
    }
```
**Design note (flagged `[ASSUMED]`, see Assumptions Log):** this pattern predicts a single horizon-endpoint price + CI, not a full day-by-day path. Render the intermediate days as a straight-line interpolation between "today's price" and the endpoint prediction, with the CI band width scaled by `sqrt(t / horizon_days)` between the two endpoints — this keeps the chart visually consistent with the SMA/Prophet models' widening-band shape without training 90 separate per-day models (see Don't Hand-Roll and Alternatives Considered for why the direct-to-endpoint strategy was chosen over per-day or recursive strategies).

### Pattern 4: Prophet — native forecast + CI, import-guarded
**What:** Prophet natively produces a full daily forecast path with `yhat`, `yhat_lower`, `yhat_upper` columns via `interval_width`.
**When to use:** The "Prophet" model option. **Must be wrapped so a failed `import prophet` (the STATE.md-flagged risk) degrades this one model option, not the whole page.**
**Example:**
```python
# src/prediction/prophet_model.py
# Source: Prophet official docs (https://facebook.github.io/prophet/docs/quick_start.html)
import logging

import pandas as pd

logger = logging.getLogger(__name__)

try:
    from prophet import Prophet

    PROPHET_AVAILABLE = True
except Exception:  # ImportError, or a cmdstanpy backend failure at import time
    logger.exception("Prophet import failed -- disabling the Prophet model option")
    PROPHET_AVAILABLE = False

INTERVAL_WIDTH = 0.80  # matches sma_model.py's Z_80PCT-implied 80% band


def forecast_forward(close: pd.Series, horizon_days: int) -> dict:
    if not PROPHET_AVAILABLE:
        raise RuntimeError("Prophet is not available in this environment")

    df = pd.DataFrame({"ds": close.index, "y": close.values})
    model = Prophet(interval_width=INTERVAL_WIDTH)
    model.fit(df)
    future = model.make_future_dataframe(periods=horizon_days)
    forecast = model.predict(future).tail(horizon_days)

    return {
        "forecast": forecast["yhat"].to_numpy(),
        "ci_lower": forecast["yhat_lower"].to_numpy(),
        "ci_upper": forecast["yhat_upper"].to_numpy(),
    }
```

### Pattern 5: D-06 "Compare all models" — modal + persistent banner + toast
**What:** `st.dialog` for the popup, `st.session_state` + `st.warning` for the persistent yellow banner (survives the dialog closing, since the computation continues after the dialog is dismissed/auto-closes), `st.toast` for the completion notification.
**When to use:** Exactly the D-06 flow — this is the one UI pattern this phase needs that no prior phase established.
**Example:**
```python
# src/pages/search.py (extended)
# API signatures confirmed against the installed streamlit==1.59.2
# environment via inspect.signature(st.dialog) / inspect.signature(st.toast)
# this research session.
import streamlit as st


@st.dialog("Comparing all models")
def _compare_all_models_dialog(ticker: str, horizon: int, feature_frame, price_df, asset_class):
    st.warning(
        "Training and backtesting all 3 models can take a while "
        "(Prophet in particular). This page will stay open while it runs."
    )
    if st.button("Start comparison"):
        st.session_state["comparing"] = True
        st.rerun()  # closes the dialog (non-dismissible pattern), work happens below


def _render_compare_all_models(ticker, horizon, feature_frame, price_df, asset_class):
    if st.session_state.get("comparing"):
        st.warning(  # persistent banner -- independent of the dialog above
            "Comparing all models for this asset -- this may take a moment."
        )
        with st.spinner("Training SMA, XGBoost, and Prophet..."):
            results = {
                model: engine.generate_forecast(ticker, model, horizon, feature_frame, price_df, asset_class)
                for model in ("sma", "xgboost", "prophet")
            }
        st.session_state["comparing"] = False
        st.session_state["compare_results"] = results
        st.toast("Model comparison ready.", icon=":material/check_circle:")
```
**Note:** `st.dialog` inherits `st.fragment` rerun-isolation behavior (interacting with a widget inside it only reruns the dialog, not the full page) — confirmed via the installed `st.dialog.__doc__` this session. Streamlit Community Cloud is a single-CPU free-tier container, so `st.fragment(parallel=True)` would not meaningfully speed up 3 CPU-bound trainings run in the same container; the sequential loop above is the correct choice, not a missed-parallelism bug.

### Pattern 6: Forecast chart with a shaded CI band (PRED-03)
**What:** Plotly's standard three-trace pattern — invisible upper-bound line, invisible lower-bound line with `fill='tonexty'`, plus the visible forecast line — extending `src/components/charts.py`'s existing pure-builder/thin-renderer split.
**Example:**
```python
# src/components/charts.py (extended)
# Source: Plotly official docs, "Continuous error bands in Python"
# (https://plotly.com/python/continuous-error-bars/) -- fill='tonexty' pattern
import plotly.graph_objects as go

FORECAST_COLOR = "#0EA5E9"
CI_FILL_COLOR = "rgba(14, 165, 233, 0.2)"


def build_forecast_figure(price_df, forecast_index, forecast_values, ci_lower, ci_upper) -> go.Figure:
    fig = build_price_history_figure(price_df)  # reuse Pattern 6's existing historical line
    fig.add_trace(go.Scatter(
        x=forecast_index, y=ci_upper, mode="lines",
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=forecast_index, y=ci_lower, mode="lines", fill="tonexty",
        fillcolor=CI_FILL_COLOR, line=dict(width=0),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=forecast_index, y=forecast_values, mode="lines",
        line=dict(color=FORECAST_COLOR, dash="dash"),
    ))
    return fig
```

### Anti-Patterns to Avoid
- **Recursive multi-step XGBoost forecasting:** feeding a 1-step-ahead prediction back in as input for the next step, repeated up to 90 times — compounds tree-model error and trees cannot extrapolate beyond their training distribution. Use the direct-horizon strategy (Pattern 3) instead.
- **Computing walk-forward folds with a hand-rolled `for i in range(...)` loop over row indices:** exactly the kind of off-by-one bug (`test_index` starting one row too early) that silently reintroduces lookahead bias. Always route through `sklearn.model_selection.TimeSeriesSplit` (Pattern 1).
- **Assembling features per-fold instead of once over the full history:** `assemble_feature_frame` must be called exactly once on the full fetched DataFrame, then sliced by fold index — never re-called on a fold's train-only slice, which would silently shrink the rolling-window warm-up period differently per fold and make folds non-comparable.
- **A single, unguarded `from prophet import Prophet` at module import time in `engine.py` or `search.py`:** if the Streamlit Cloud build environment's Prophet install is degraded (Pitfall 1), this crashes the entire page, not just the Prophet option. Import-guard it (Pattern 4) so `PROPHET_AVAILABLE = False` degrades gracefully.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Expanding-window walk-forward train/test index generation | A custom loop computing `train_end`/`test_start`/`test_end` row offsets | `sklearn.model_selection.TimeSeriesSplit(n_splits, test_size)` | Off-by-one errors here directly cause the exact lookahead-bias failure mode PRED-04 exists to prevent; this is an already-tested, one-line stdlib-adjacent call |
| XGBoost prediction intervals | A bespoke residual-variance heuristic bolted onto a point-estimate model | XGBoost's native `objective="reg:quantileerror"` (available since XGBoost 2.0, satisfied by the pinned 3.3.0) | Purpose-built, well-documented, CPU-cheap, and evaluated with a proper scoring rule (pinball loss) rather than an ad hoc formula |
| Sharpe ratio / directional accuracy / RMSE | Independent formula implementations scattered across model modules | One shared `src/prediction/metrics.py`, called identically by every model's backtest path | Guarantees all three models are compared on the exact same metric definitions (same annualization factor, same directional-accuracy tie-break rule) — otherwise "Compare all models" (D-06) would be comparing apples to oranges |
| Plotly confidence-interval shading | Custom SVG/CSS overlay, or per-point manual polygon math | The standard `fill='tonexty'` three-trace Scatter pattern (Pattern 6) | Well-documented, officially supported Plotly idiom; matches the project's existing `plotly.graph_objects`-based chart-building convention |

**Key insight:** every "don't hand-roll" item above exists precisely because a subtly wrong hand-rolled version would still *look* correct in a demo (chart renders, numbers appear) while silently violating PRED-04's no-lookahead-bias requirement or D-06's apples-to-apples comparison requirement. Prefer the audited library call every time one exists.

## Common Pitfalls

### Pitfall 1: Prophet/cmdstanpy Streamlit Cloud build-time failure (STATE.md-flagged)
**What goes wrong:** `pip install prophet` fails, hangs, or silently falls back to a from-source CmdStan compile during Streamlit Community Cloud's build step, either exceeding the build time budget or failing outright with "Cannot connect to CmdStan github repo".
**Why it happens:** Since Prophet 1.1, PyPI ships prebuilt `manylinux` wheels with CmdStan already compiled and bundled inside `[VERIFIED: web search — Prophet GitHub PR #2010/#2041, build process downloads+compiles+prunes CmdStan to <20MB inside the wheel]`, which should make this a non-issue for a standard Linux x86_64 `pip install`. However, an **unresolved** Streamlit Community forum thread (`[CITED: discuss.streamlit.io/t/cmdstan-in-streamlit-cloud/120318]`) documents exactly this failure mode with no working fix reported, and the thread auto-closed after 180 days with the issue still open. The two findings are not necessarily contradictory — the forum poster may have hit the *fallback* `cmdstanpy.install_cmdstan()` path (e.g. via conda, or a version mismatch that made pip fall back to the sdist) rather than the normal prebuilt-wheel path.
**How to avoid:** (1) Pin `prophet==1.2.1` (well past the 1.1 wheel-bundling change) exactly as `CLAUDE.md` specifies. (2) During Phase 4 execution, treat the first real Streamlit Community Cloud deploy with Prophet installed as a mandatory empirical checkpoint — verify the build log shows a wheel install, not a compile step, and time the first `Prophet().fit()` call. (3) Implement the import-guard from Pattern 4 regardless of whether the empirical check passes, so a future Streamlit Cloud base-image change can't silently break the whole page. (4) If the empirical check fails, the documented fallback is disabling the Prophet UI option with the same D-08 non-blocking-message pattern already used for insufficient history.
**Warning signs:** Build step taking materially longer than the other two dependencies; build log mentioning `install_cmdstan` or a `github.com/stan-dev/cmdstan` download; `ImportError` or a `subprocess`-related exception on first `import prophet` in the deployed app's logs.

### Pitfall 2: Reusing Phase 3's 1-year fetch window / 20-row minimum-history gate
**What goes wrong:** If prediction code calls `fetch_ohlcv(ticker)` with the default `period="1y"` (~252 trading days) and gates on the existing `MIN_HISTORY_ROWS = 20`, walk-forward backtesting will either fail outright (not enough rows for `TimeSeriesSplit` to produce 5 folds at a 90-day test size) or silently produce statistically meaningless backtest metrics from too few folds.
**Why it happens:** `MIN_HISTORY_ROWS = 20` (Phase 3, `src/recommendation/universe.py`) was sized for "compute one point-in-time feature row" — it says nothing about how much history a *multiple-fold* walk-forward backtest needs.
**How to avoid:** Use a dedicated, stricter threshold. **Recommended: `MIN_PREDICTION_HISTORY_ROWS = 750`** (post-`dropna` feature rows), derived as follows and visibly larger than 20 per D-07's requirement:
- Initial (fold-1) train window: **252 rows** (one trading year) — the minimum needed for Prophet's yearly-seasonality component to have a full cycle to fit, and enough rows for XGBoost to see more than one market regime.
- Fold count: **5** — enough for a stable average metric (a single fold's RMSE/directional-accuracy is not trustworthy; 3 is a bare minimum, 5 gives real headroom) while staying cheap on free-tier CPU (5× SMA fits are instant, 5× XGBoost fits are seconds, 5× Prophet fits are the real cost budget item).
- Worst-case test window: **90 days** (the largest of the D-03 horizon presets) — the threshold must support the largest horizon since D-08's button-disable is asset-level, not horizon-level.
- `252 + 5 × 90 = 702` rows minimum for `TimeSeriesSplit(n_splits=5, test_size=90)` to succeed; **750** adds a small safety margin.
Fetch with `fetch_ohlcv(ticker, period="5y")` for prediction contexts specifically (a new call site, not a change to the chokepoint's default) — 5 years of daily data (~1,260 trading-day rows for equities/ETFs/gold-futures/forex, more for 7-day-a-week crypto) comfortably clears 750 for any asset with a real trading history, while correctly triggering D-08's insufficient-data path for recent IPOs/new crypto tokens.
**Warning signs:** `TimeSeriesSplit` raising `ValueError: Too many splits=N for number of samples`; backtest metrics with visibly high fold-to-fold variance (a symptom of too few folds).

### Pitfall 3: `fetch_ohlcv`'s cache key includes `period`, so a second `st.cache_data`/SQLite entry is created — not a conflict, but a doubling of cached rows per ticker
**What goes wrong:** None functionally, but worth flagging so it isn't "fixed" as a bug: since `src/pages/recommendations.py`/`search.py`'s existing score-path calls `fetch_ohlcv(ticker)` (period="1y" default) and the new `_prediction_loader.py` calls `fetch_ohlcv(ticker, period="5y")`, the same ticker now has two independent SQLite `price_cache` rows (keyed on `(ticker, period)`) and two independent `st.cache_data` cache entries.
**Why it happens:** `fetch_ohlcv`'s `@st.cache_data(ttl=CACHE_TTL_SECONDS)` decorator and its SQLite `PRIMARY KEY (ticker, period)` both key on the full `(ticker, period)` tuple `[VERIFIED: src/data/cache.py, read this session]`.
**How to avoid:** No code change needed — this is by design and confirmed safe by reading `cache.py` directly. Just don't assume a `period="1y"` fetch's cache entry can serve a `period="5y"` request or vice versa; they are, correctly, two independent cache rows.
**Warning signs:** None expected; flagged purely so a future contributor doesn't "consolidate" this into one shared fetch and accidentally under-fetch history for prediction or over-fetch for scoring.

### Pitfall 4: Leakage smoke test must target the *split*, not just the feature computation
**What goes wrong:** Phase 2's leakage smoke test (`tests/test_features_leakage.py`, D-11 pattern) already proves `assemble_feature_frame` never lets a future row's `Close` value influence an earlier row's feature value. It is tempting to consider PRED-04's no-lookahead-bias requirement "already covered" by that test — it is not. The new leakage risk in this phase is entirely in the **fold-splitting and per-fold fit/predict loop**, a code path that didn't exist in Phase 2.
**Why it happens:** `assemble_feature_frame` being leak-proof (point-in-time rolling windows) is a *necessary* but not *sufficient* condition — a backtest harness can still leak by fitting a model on a `train_index` that accidentally includes rows from `test_index`, or by fitting the SMA/XGBoost model on the *full* history before slicing predictions per fold (which would let fold 1's "prediction" implicitly benefit from having seen fold 5's data during a single global `.fit()` call).
**How to avoid:** Add a dedicated smoke test in `src/prediction/`'s test suite, following the exact D-11 pattern: (1) assert structurally, for every fold returned by `walk_forward.make_folds`, that `max(train_index) < min(test_index)` (no overlap, correct ordering); (2) the synthetic-signal-injection variant — perturb a `Close` value inside a fold's test window only, refit, and assert the *previous* folds' backtest metrics are byte-for-byte unchanged (mirrors `test_synthetic_future_signal_never_appears_before_its_source_date`).
**Warning signs:** Backtest RMSE/directional-accuracy metrics that look "too good" (e.g., >95% directional accuracy) — the classic symptom of a leaky backtest, exactly the failure mode D-11's pattern exists to catch.

### Pitfall 5: Sharpe ratio annualization factor differs by asset class
**What goes wrong:** Using a flat `sqrt(252)` annualization factor for every asset silently understates crypto's (and, less dramatically, forex's) Sharpe ratio, since crypto trades 7 days/week (~365 data points/year) versus equities/ETFs/gold-futures' ~252 trading-day calendar.
**Why it happens:** The classic Sharpe formula (`mean(returns) / std(returns) * sqrt(periods_per_year)`) assumes a fixed trading-period count that is genuinely different across this project's five supported asset classes — a fact Phase 3's research already surfaced for factor normalization (D-03 in `03-CONTEXT.md`) and applies here too.
**How to avoid:** `src/prediction/metrics.py`'s Sharpe function must take `asset_class` as an explicit parameter and select `365` for `"crypto"`, `252` for everything else (stocks, ETFs, gold, forex) — matching the asset-class-aware pattern already established in `src/recommendation/`. Document the exact long/short signal-following strategy construction used to derive the "captured returns" series feeding Sharpe as `[ASSUMED]` (see Assumptions Log) since CONTEXT.md does not specify it.
**Warning signs:** Crypto backtest Sharpe ratios that look implausibly low compared to equities for a similarly-accurate model.

### Pitfall 6: `st.cache_data` on prediction/backtest results without a bound — expensive recompute on every rerun otherwise
**What goes wrong:** Streamlit reruns the whole script on every interaction; without caching, clicking "Generate Forecast" twice (or any unrelated widget interaction after generating a forecast) retrains XGBoost/Prophet from scratch every time.
**Why it happens:** Same rerun-per-interaction model that makes `st.cache_data` "mandatory, not optional" everywhere else in this project per `CLAUDE.md`.
**How to avoid:** Cache `engine.generate_forecast(ticker, model, horizon, ...)` (or its constituent per-model calls) via `st.cache_data(ttl=CACHE_TTL_SECONDS)` (reuse the existing `src/config.py` constant, or a dedicated longer TTL — price/feature data underlying a forecast doesn't change intra-hour) keyed on `(ticker, model, horizon)`. This directly benefits D-06's "Compare all models" too: if the user already generated an SMA forecast individually, "Compare all models" should hit that cache entry rather than retraining SMA a second time.
**Warning signs:** Repeated multi-second UI freezes on unrelated widget interactions after a forecast has already been generated once.

## Code Examples

### Backtest metrics (RMSE / directional accuracy / Sharpe), asset-class-aware
```python
# src/prediction/metrics.py
# Source: standard quant-finance formulas (RMSE, hit-rate/directional
# accuracy, annualized Sharpe) -- textbook definitions, not library-specific
import numpy as np

TRADING_DAYS_PER_YEAR = {"crypto": 365}
DEFAULT_TRADING_DAYS_PER_YEAR = 252  # stocks, ETFs, gold futures, forex


def rmse(predicted: np.ndarray, actual: np.ndarray) -> float:
    return float(np.sqrt(np.mean((predicted - actual) ** 2)))


def directional_accuracy(predicted_direction: np.ndarray, actual_direction: np.ndarray) -> float:
    """Both arrays are +1/-1 (or 0 for no-change) sign arrays of price
    change over each backtest fold's horizon."""
    return float(np.mean(predicted_direction == actual_direction))


def sharpe_ratio(captured_returns: np.ndarray, asset_class: str) -> float:
    """captured_returns: the daily return series realized by a
    signal-following long/short strategy driven by this model's predicted
    direction each backtest day (ASSUMED strategy construction -- see
    Assumptions Log A-05)."""
    periods_per_year = TRADING_DAYS_PER_YEAR.get(asset_class, DEFAULT_TRADING_DAYS_PER_YEAR)
    std = captured_returns.std()
    if std == 0:
        return 0.0
    return float(captured_returns.mean() / std * np.sqrt(periods_per_year))
```

### Leakage smoke test for the walk-forward split (extends the D-11 pattern)
```python
# tests/test_prediction_walk_forward.py
# Adapted from tests/test_features_leakage.py's D-11 pattern for this
# phase's new split-generation code path (Pitfall 4).
from src.prediction.walk_forward import make_folds


def test_folds_never_overlap_and_test_always_after_train():
    folds = make_folds(n_rows=750, horizon_days=90, n_folds=5)
    for train_index, test_index in folds:
        assert max(train_index) < min(test_index)


def test_expanding_window_train_sets_are_supersets():
    folds = make_folds(n_rows=750, horizon_days=90, n_folds=5)
    for (train_a, _), (train_b, _) in zip(folds, folds[1:]):
        assert set(train_a).issubset(set(train_b))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| PyStan backend for Prophet, requiring a C++ compile of the Stan model per install | CmdStanPy backend with prebuilt wheels bundling a precompiled CmdStan binary | Prophet 1.0 (backend swap) / 1.1 (prebuilt wheel distribution) | Directly de-risks the STATE.md-flagged concern — `pip install prophet` on a standard Linux x86_64 target should not require a compiler at all in the common case |
| Simple `train_test_split` (random shuffle) for model evaluation | `TimeSeriesSplit` expanding-window walk-forward validation | Long-standing best practice for any time-series problem, not a recent change, but worth stating explicitly since a random shuffle split is the single most common time-series-evaluation mistake | A random split would leak future information into training folds, invalidating PRED-04's no-lookahead-bias requirement entirely |
| Point-estimate-only regression + a hand-tuned error margin for a "confidence interval" | Native quantile regression (`reg:quantileerror`) for tree models | XGBoost 2.0 (2023) added `reg:quantileerror`/`QuantileDMatrix` | Removes the need for a bespoke, unvalidated CI heuristic for the XGBoost model specifically |

**Deprecated/outdated:**
- `fbprophet` package name: renamed to `prophet` as of v1.0 — `CLAUDE.md` already correctly uses the new name.
- PyStan-backed Prophet installs (pre-1.0): long superseded; not relevant to the pinned `1.2.1`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A-01 | `MIN_PREDICTION_HISTORY_ROWS = 750`, with `n_folds=5` and initial train window `252` | Common Pitfalls, Pitfall 2 | If too low: unstable/misleading backtest metrics from too few effective folds. If too high: unnecessarily excludes newer-but-still-viable assets from the prediction feature entirely. This is Claude's-discretion per CONTEXT.md D-07, but the exact number should be confirmed with the user/planner before being treated as immovable. |
| A-02 | `fetch_ohlcv(ticker, period="5y")` is the right fetch window for prediction (vs. Phase 3's `1y`) | Architectural Responsibility Map, Pitfall 2 | If yfinance's 5y history is inconsistently available across asset classes (e.g., very new ETFs), more assets than expected will fall into the D-08 insufficient-data path — acceptable per D-08's design but should be watched during execution. |
| A-03 | XGBoost uses a "direct-to-horizon-endpoint" strategy with linear interpolation + sqrt-scaled CI for the intermediate path (not a full per-day model) | Architecture Patterns, Pattern 3 | If a full daily forecast path (not just the endpoint) is a hard UX requirement for XGBoost specifically, this design under-delivers — worth confirming with the user during planning/discuss-phase if the interpolated-path visual is unacceptable. |
| A-04 | SMA baseline CI uses the Gaussian "square-root-of-time" heuristic (`± z·σ·√t`), not a bootstrap | Alternatives Considered, Pattern 2 | If backtest data shows daily returns are strongly non-normal (fat tails) for some asset class, this CI could be systematically too narrow — a bootstrap-based CI would be more robust but costs more compute for a "baseline" model. |
| A-05 | Sharpe ratio is computed from a signal-following long/short strategy driven by each model's predicted direction each backtest day, not a buy-and-hold or long-only construction | Code Examples, Pitfall 5 | CONTEXT.md does not specify this; a different construction (e.g., long-only, or magnitude-weighted position sizing) would produce different Sharpe numbers for the same underlying model quality. Also interacts with COMPLY-02 (non-directive language) — the UI must present this as a descriptive backtest statistic ("Simulated Sharpe, signal-following"), never as trading guidance. |
| A-06 | `st.toast()` is the right widget for D-06's completion notification | Architecture Patterns, Pattern 5 | Low risk — `st.toast` is explicitly named as an option in CONTEXT.md's own discretion note; `st.success` inside the persistent banner area is a safe fallback if `st.toast`'s auto-dismiss timing feels too easy to miss during UAT. |
| A-07 | Prophet's `interval_width=0.80` is set to match the SMA baseline's 80% CI so all three models' bands are visually comparable when switching the D-01 dropdown | Architecture Patterns, Pattern 4 | If the user expects Prophet's default (also 0.80 in Prophet itself, so actually a non-issue) or a different width (e.g. 95%) per model, this would need to change — low risk since 0.80 is also Prophet's own out-of-the-box default. |

**If this table is empty:** N/A — see entries above.

## Open Questions

1. **Does the "Compare all models" side-by-side view need its own dedicated backtest-metrics table component, or does it reuse the D-05 single-model metrics table three times?**
   - What we know: D-06 says "see all 3 models' backtest metrics side-by-side" but doesn't specify layout (columns? one table with a model column?).
   - What's unclear: Whether this is a planner-level UI-SPEC decision or needs another user round.
   - Recommendation: Treat as a UI-SPEC-phase (or planner) decision — likely `st.columns(3)` each rendering the same D-05-style metrics table, mirroring how Phase 3 already reuses one chart-building function at multiple sizes (`build_breakdown_figure`). Not a research gap, a layout decision.

2. **Should `src/prediction/`'s trained models be cached as `st.cache_resource` objects (reusable across reruns without a full refit) in addition to caching the `st.cache_data`-wrapped `generate_forecast` result dict?**
   - What we know: `st.cache_resource` is the documented pattern for "objects that can't be serialized" (e.g. ML models); `generate_forecast`'s *output* (forecast arrays + CI + metrics dict) is plain serializable data, appropriate for `st.cache_data`.
   - What's unclear: Whether there's ever a case where the same fitted model object (not just its output) needs to be reused across two different calls (e.g., re-predicting a different horizon without a full refit) — unlikely given the direct-horizon XGBoost strategy retrains per horizon anyway, and Prophet's `make_future_dataframe` already supports multiple horizons off one `.fit()`.
   - Recommendation: `st.cache_data` on `generate_forecast`'s output dict is sufficient for v1; don't add `st.cache_resource` model-object caching unless profiling during execution shows it's needed.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Entire stack | ✓ (local dev) | 3.13.7 | `CLAUDE.md` recommends 3.11/3.12 for Streamlit Cloud wheel-availability safety margin; this dev machine runs 3.13.7, which is a mismatch worth resolving via a `runtime.txt`/Streamlit Cloud "Python version" deploy setting (no such pin exists in the repo yet — none of `.python-version`, `runtime.txt`, `packages.txt` were found) |
| xgboost | PRED-02 | ✗ (not yet installed) | — | `pip install --dry-run` confirms a clean prebuilt-wheel resolution on this machine; no fallback needed, install per Standard Stack |
| prophet | PRED-02 | ✗ (not yet installed) | — | `pip install --dry-run` confirms a clean prebuilt-wheel resolution (including `cmdstanpy`) on this machine; production risk is Streamlit Cloud's build image specifically, not local dev (see Pitfall 1) — fallback is the import-guard pattern (Pattern 4), not a different package |
| scikit-learn | PRED-04 (`TimeSeriesSplit`) | ✗ (not yet installed) | — | No fallback needed — trivial pure-Python dependency, no compiled-extension risk |
| C++ compiler / `make` in Streamlit Cloud build image | Prophet's CmdStan fallback path only (not the normal prebuilt-wheel path) | Unknown — could not be verified from this research session (no access to Streamlit Cloud's actual build container) | — | If the prebuilt-wheel path fails for any reason during Phase 4's empirical validation, this becomes the blocking dependency; no `packages.txt` entry currently exists in the repo to add `build-essential` as a fallback |

**Missing dependencies with no fallback:** None — all three ML libraries have a documented, low-risk install path; the one genuine unknown (Streamlit Cloud build-image compiler availability) only matters if the prebuilt-wheel path fails, which is an execution-time empirical check per STATE.md, not a research-time blocker.

**Missing dependencies with fallback:** `prophet` — fallback is the import-guard UI degradation pattern (Pattern 4), not a different package or version.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already configured via `pyproject.toml`'s `[tool.pytest.ini_options]`) |
| Config file | `pyproject.toml` (`testpaths = ["tests"]`, `pythonpath = ["."]`) |
| Quick run command | `pytest tests/test_prediction_*.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRED-01 | Historical price chart renders for any resolved ticker | unit (reuses Phase 3's `render_price_history_chart` path — no new test needed beyond confirming the extended `search.py` still calls it) | `pytest tests/test_components.py -x` | ✅ (existing) |
| PRED-02 | Model dropdown + horizon selector + Generate Forecast button produce a forecast for each of the 3 models | unit | `pytest tests/test_prediction_sma.py tests/test_prediction_xgboost.py tests/test_prediction_prophet.py -x` | ❌ Wave 0 |
| PRED-03 | Forecast + CI band render correctly (CI widens with horizon; `ci_lower <= forecast <= ci_upper` for every point) | unit | `pytest tests/test_prediction_ci.py -x` | ❌ Wave 0 |
| PRED-04 | Walk-forward backtest produces RMSE/directional accuracy/Sharpe with no lookahead bias | unit (structural split test + D-11-style synthetic-signal-injection smoke test) | `pytest tests/test_prediction_walk_forward.py tests/test_prediction_backtest.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_prediction_*.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_prediction_walk_forward.py` — covers PRED-04 fold-generation correctness (Pattern 1, Pitfall 4)
- [ ] `tests/test_prediction_sma.py` — covers PRED-02/PRED-03 for the SMA baseline (Pattern 2)
- [ ] `tests/test_prediction_xgboost.py` — covers PRED-02/PRED-03 for XGBoost (Pattern 3); use small synthetic fixtures (≤750 rows) to keep training time bounded
- [ ] `tests/test_prediction_prophet.py` — covers PRED-02/PRED-03 for Prophet (Pattern 4); **expect this file's tests to be the slowest in the suite** (Prophet fits take multiple seconds even on tiny synthetic data) — keep synthetic fixtures as small as the `MIN_PREDICTION_HISTORY_ROWS` threshold allows, and consider one real-fit integration test plus mocked-fit tests for the orchestration logic, rather than many real fits
- [ ] `tests/test_prediction_backtest.py` — covers PRED-04's D-11-style leakage smoke test (Code Examples) and asset-class-aware Sharpe (Pitfall 5)
- [ ] `tests/test_prediction_loader.py` — covers the new `_prediction_loader.py`'s `MIN_PREDICTION_HISTORY_ROWS` gate (D-07/D-08), mirroring `tests/test_universe_loader.py`'s existing shape
- [ ] Framework install: none needed — `pytest` already configured; only the three new production dependencies (`xgboost`/`prophet`/`scikit-learn`) need installing

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | Unchanged — `require_auth()` reused verbatim, no new auth surface this phase |
| V3 Session Management | No | Unchanged |
| V4 Access Control | Yes (reused, not new) | `require_auth()` gate already applied at the top of `search.py`; the new model/horizon controls and Compare-all-models action are simply additional widgets on the same already-gated page |
| V5 Input Validation | Yes | Model selector and horizon selector are both closed enum sets (`st.selectbox` constrains the UI, but the `generate_forecast(ticker, model, horizon, ...)` entry point must independently validate `model in {"sma", "xgboost", "prophet"}` and `horizon in {7, 30, 90}` server-side, never trust the widget alone — same discipline as any allow-list validation) |
| V6 Cryptography | No | No new secrets/crypto introduced this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Free-tier CPU exhaustion via repeated "Generate Forecast"/"Compare all models" clicks (new risk this phase — Phase 3 had no CPU-heavy compute) | Denial of Service | `st.cache_data`-based memoization of `generate_forecast` results per `(ticker, model, horizon)` (Pitfall 6) is the primary mitigation — a cached result serves instantly on repeat clicks instead of retraining; disabling the button while a spinner is active (Streamlit's synchronous execution model already blocks further widget interaction during a running script) is the secondary mitigation |
| Supply-chain risk from installing 3 new external packages, one of which (`prophet`) triggers a compiled-artifact install path | Tampering | Package Legitimacy Audit above + `checkpoint:human-verify` before pinning (existing project pattern from Phase 3's `numpy`/`plotly`) |
| Untrusted ticker string reaching a new fetch call (`fetch_ohlcv(ticker, period="5y")`) | Tampering/Injection | Already mitigated by Phase 1/3's existing chokepoint discipline — `fetch_ohlcv` never interpolates `ticker` into SQL (parameterized `?` placeholders, confirmed by reading `cache.py` this session) and yfinance itself rejects malformed symbols; no new validation needed beyond what Phase 3 already established for the same `ticker` value |

## Sources

### Primary (HIGH confidence)
- `pip index versions xgboost / prophet / scikit-learn / cmdstanpy` — direct PyPI registry query, this session
- `pip install --dry-run xgboost==3.3.0 / prophet==1.2.1 / scikit-learn==1.9.0` — direct dependency-resolution check against this machine's Python 3.13 environment, this session
- `src/data/cache.py`, `src/features/feature_frame.py`, `src/pages/search.py`, `src/components/charts.py`, `src/pages/_universe_loader.py`, `src/recommendation/engine.py`, `src/recommendation/universe.py`, `src/components/disclaimer.py`, `requirements.txt`, `.planning/config.json` — read directly, this session
- `inspect.signature(st.dialog)`, `inspect.signature(st.toast)`, `inspect.signature(st.fragment)`, `st.dialog.__doc__` — introspected directly against the installed `streamlit==1.59.2` package, this session

### Secondary (MEDIUM confidence)
- [XGBoost Quantile Regression official docs](https://xgboost.readthedocs.io/en/stable/python/examples/quantile_regression.html) — `reg:quantileerror` objective, `quantile_alpha` parameter
- [Plotly "Continuous error bands in Python"](https://plotly.com/python/continuous-error-bars/) — `fill='tonexty'` CI-band pattern
- [scikit-learn `TimeSeriesSplit` behavior](https://machinelearningmastery.com/backtest-machine-learning-models-time-series-forecasting/) — walk-forward/expanding-window validation, cross-checked against multiple independent sources (MachineLearningMastery, Analytics Vidhya, skforecast docs)
- [Multi-step forecasting: direct vs. recursive strategy comparison](https://letsdatascience.com/blog/multi-step-time-series-forecasting-recursive-direct-and-hybrid-strategies) — cross-checked against `xgboosting.com` and `machinelearningmastery.com`
- Prophet PyPI wheel-bundling of CmdStan since 1.1 — cross-checked across the Prophet GitHub PR #2010 discussion, PR #2041 discussion, and community "Facebook Prophet in 2023 and beyond" writeup

### Tertiary (LOW confidence)
- [Streamlit Community forum: "CmdStan in Streamlit Cloud"](https://discuss.streamlit.io/t/cmdstan-in-streamlit-cloud/120318) — single unresolved forum thread, no working fix documented; treated as a real risk signal but not proof the prebuilt-wheel path (the normal `pip install prophet` path) actually fails on Streamlit Cloud specifically — flagged for mandatory empirical validation during Phase 4 execution per STATE.md

## Metadata

**Confidence breakdown:**
- Standard stack (xgboost/prophet/scikit-learn versions, wheel availability): HIGH — directly verified against the live PyPI registry and a real dependency-resolution dry-run this session
- Walk-forward architecture (`TimeSeriesSplit`, fold/window scheme): MEDIUM-HIGH — the `TimeSeriesSplit` mechanism is officially documented and standard; the specific `750`-row/`5`-fold/`252`-train-window numbers are a synthesized, justified recommendation (`[ASSUMED]`, A-01) since CONTEXT.md explicitly delegates this to research/planning discretion
- Prophet/Streamlit Cloud cold-start risk: MEDIUM — cross-checked from multiple angles (official wheel-bundling change, an unresolved community forum report, a dependency dry-run on this machine) but genuinely cannot be fully resolved without executing an actual Streamlit Cloud deploy, which STATE.md correctly flags as an execution-time, not research-time, task
- Per-model CI computation (Prophet native / XGBoost quantile / SMA sqrt-time): MEDIUM-HIGH for Prophet and XGBoost (both are documented library features); MEDIUM for the SMA heuristic specifically, since the exact CI-width/strategy choice is `[ASSUMED]` (A-04)
- Pitfalls: HIGH for the codebase-integration pitfalls (verified by reading the actual source files); MEDIUM for the Prophet cold-start pitfall (see above)

**Research date:** 2026-08-09
**Valid until:** 30 days for the codebase-integration findings (stable, based on committed source); 14 days for the Prophet/Streamlit Cloud build-risk findings specifically, given `[CITED]` community-sourced material can go stale quickly and STATE.md already requires re-validation at execution time regardless
