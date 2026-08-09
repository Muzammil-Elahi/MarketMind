# Phase 4: Multi-Model Prediction + Walk-Forward Backtesting - Pattern Map

**Mapped:** 2026-08-09
**Files analyzed:** 9 (new + modified)
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/prediction/__init__.py` | package init | — | `src/recommendation/__init__.py` | exact |
| `src/prediction/walk_forward.py` | utility (pure transform) | batch/transform | `src/recommendation/similarity.py` | role-match |
| `src/prediction/sma_model.py` | service (model) | transform | `src/recommendation/factor_scoring.py` | role-match |
| `src/prediction/xgboost_model.py` | service (model) | transform | `src/recommendation/factor_scoring.py` | role-match |
| `src/prediction/prophet_model.py` | service (model, import-guarded) | transform | `src/recommendation/factor_scoring.py` | partial (needs new import-guard pattern, no existing analog) |
| `src/prediction/metrics.py` | utility | batch/transform | `src/recommendation/explain.py` | role-match |
| `src/prediction/backtest.py` | service (orchestrator) | batch | `src/recommendation/engine.py` (`score_universe`) | role-match |
| `src/prediction/engine.py` | service (orchestrator) | request-response | `src/recommendation/engine.py` (`score_universe`/`build_recommendations`) | exact |
| `src/pages/_prediction_loader.py` | utility (I/O loader) | CRUD/file-I/O | `src/pages/_universe_loader.py` | exact |
| `src/pages/search.py` (extended) | controller (page) | request-response | `src/pages/search.py` (itself, pre-existing) | exact |
| `src/components/charts.py` (extended: `build_forecast_figure`/`render_forecast_chart`) | component (chart builder) | transform | `src/components/charts.py` (`build_price_history_figure`/`render_price_history_chart`) | exact |
| `tests/test_prediction_leakage.py` (new, D-11-style smoke test) | test | — | `tests/test_features_leakage.py` | exact |

## Pattern Assignments

### `src/prediction/engine.py` (service, request-response orchestrator)

**Analog:** `src/recommendation/engine.py`

**Module docstring / zero-I/O contract convention** (lines 1-13):
```python
"""Zero-I/O scoring orchestrator (REC-01/REC-02/REC-03, D-05).

`score_universe` is the single scoring pipeline both the ranked-list page
and the search/drill-in page call (REC-04's single-source-of-truth
requirement) -- it never reimplements any sibling module's math inline,
only assembles their outputs.

This module performs zero network, database, or LLM calls. It imports
only ``pandas``, the standard library, and sibling
``src.recommendation`` modules -- never ``streamlit``, ``yfinance``,
``sqlite3``, or any agent-orchestration/generative-AI SDK symbol.
"""
```
Apply verbatim for `src/prediction/engine.py`: same zero-I/O contract sentence, swapping `src.recommendation` for `src.prediction`, and explicitly noting `xgboost`/`prophet` training happens in-process (CPU) but still counts as "zero I/O" (no network/db/LLM calls).

**Orchestrator signature + single-entry-point pattern** (lines 50-67):
```python
def score_universe(
    profile: dict, universe_df: pd.DataFrame, apply_hard_exclude: bool = True
) -> pd.DataFrame:
    """Score every eligible row of `universe_df` against `profile`.
    ...
    """
    if universe_df.empty:
        return universe_df
    ...
```
Mirror this for `generate_forecast(ticker, model, horizon, feature_frame, price_df, asset_class)` — one function is the entry point every page call routes through (never duplicated per page), empty/degenerate input handled defensively up front before any model-specific math runs.

**Composition-not-reimplementation pattern** (lines 82-96): `score_universe` never inlines factor math — it calls `factor_scoring.compute_momentum_score`, `profile_fit.compute_profile_fit`, `similarity.similarity_score` and assembles their outputs. `engine.py`'s `generate_forecast` must do the same: dispatch to `walk_forward.make_folds`, `<model>.fit_predict`/`forecast_forward`, `metrics.compute_backtest_metrics` — never compute RMSE/Sharpe/CI math inline in `engine.py`.

**Deterministic, documented return-shape docstring convention** (lines 50-67, also `build_recommendations` lines 124-144): every public function's docstring enumerates every possible returned dict shape/status explicitly. Apply the same enumerated-shape docstring style to `generate_forecast`'s return dict (`{forecast, ci_lower, ci_upper, backtest_metrics}` / degraded-model variants).

---

### `src/prediction/walk_forward.py`, `metrics.py`, `sma_model.py`, `xgboost_model.py` (pure transform utilities)

**Analog:** `src/recommendation/factor_scoring.py` / `src/recommendation/similarity.py` / `src/recommendation/explain.py` (all zero-I/O, pure-function modules under `src/recommendation/`)

**Convention to copy:** each sibling module is a flat set of pure functions operating on already-fetched `pd.DataFrame`/`pd.Series` — no `streamlit`, no `fetch_ohlcv`, no side effects. Follow the exact `04-RESEARCH.md` Pattern 1/2/3 code (already vetted against this codebase's conventions) for `walk_forward.make_folds`, `sma_model.forecast_forward`, `xgboost_model.fit_predict`. Module-level constants (e.g. `WEIGHTS`, `TOP_N_PER_CLASS` in `engine.py`; `MIN_HISTORY_ROWS` in `universe.py`) are declared at the top of the module with a one-line comment explaining the chosen value — apply this to `N_FOLDS`, `QUANTILES`, `Z_80PCT`, `MIN_PREDICTION_HISTORY_ROWS`.

**Rounding/precision defensiveness convention** (`engine.py` lines 36-47, `_round_half_up` / `_compose_score` clamped to `[0, 100]`): apply the same defensive-clamping instinct to `metrics.py` — e.g. `directional_accuracy` bounded to `[0, 1]`, Sharpe guarded against `std == 0` (division-by-zero returns `0.0`, matching the `if std == 0: return 0.0` snippet already drafted in RESEARCH.md's Code Examples).

---

### `src/prediction/prophet_model.py` (import-guarded model)

**No close in-repo analog** — this codebase has no existing "optional dependency, degrade gracefully" pattern. RESEARCH.md's Pattern 4 (`try: from prophet import Prophet ... except Exception: PROPHET_AVAILABLE = False`) is the only available template; combine it with `_universe_loader.py`'s status-dict convention below so `PROPHET_AVAILABLE=False` maps cleanly onto a `{"status": "unavailable"}`-style result the page can render via the existing `st.warning`/`st.error` idiom already used in `search.py` (lines 129-137).

**Logging-on-failure convention** (`_universe_loader.py` lines 38-42):
```python
try:
    df, _source = fetch_ohlcv(ticker)
except Exception:
    logger.exception("fetch_scorable_row failed for %s", ticker)
    return {"status": "not_found"}
```
Apply the same `logger.exception(...)` + graceful-status-return shape to the Prophet import guard and to any per-fold Prophet fit failure inside `backtest.py`.

---

### `src/pages/_prediction_loader.py` (I/O loader)

**Analog:** `src/pages/_universe_loader.py` (full file read — 96 lines, all extracted, no re-read needed)

**Module docstring / "why this lives under pages/ not the pure package" convention** (lines 1-13):
```python
"""Shared fetch + assemble + minimum-history gate for one asset (D-07/D-08).

Unlike ``src/recommendation/``, this module performs I/O -- it is
deliberately located under ``src/pages/`` rather than ``src/recommendation/``
for that reason. Both ``src/pages/recommendations.py`` (Plan 06) and
``src/pages/search.py`` (Plan 07) import from here rather than duplicating
the fetch-and-assemble loop.
"""
```
Copy verbatim (swap package names) for `_prediction_loader.py`'s docstring, explicitly citing why it lives under `src/pages/` not `src/prediction/`.

**Status-dict discriminated-union return convention** (lines 24-63):
```python
def fetch_scorable_row(ticker: str, asset_class: str, sector: str | None) -> dict:
    """...
    Returns one of:
    - ``{"status": "not_found"}`` ...
    - ``{"status": "insufficient_data", "chart_df": df}`` ...
    - ``{"status": "ok", "chart_df": df, "feature_row": {...}}`` ...
    """
    try:
        df, _source = fetch_ohlcv(ticker)
    except Exception:
        logger.exception("fetch_scorable_row failed for %s", ticker)
        return {"status": "not_found"}

    if df.empty:
        return {"status": "not_found"}

    feature_frame = assemble_feature_frame(df).dropna()
    if len(feature_frame) < MIN_HISTORY_ROWS:
        return {"status": "insufficient_data", "chart_df": df}

    last_row = feature_frame.iloc[-1]
    return {"status": "ok", "chart_df": df, "feature_row": {...}}
```
Apply directly for a new `fetch_prediction_data(ticker, asset_class, sector)`:
- Same `try/except Exception: logger.exception(...); return {"status": "not_found"}` around `fetch_ohlcv(ticker, period="5y")` (note the new `period="5y"` argument per RESEARCH.md Pitfall 2/3 — a distinct SQLite/`st.cache_data` cache row from the existing `period="1y"` call site, by design, no chokepoint change needed).
- Same `if df.empty: return {"status": "not_found"}` gate.
- Swap `MIN_HISTORY_ROWS` (20, from `src.recommendation.universe`) for a new `MIN_PREDICTION_HISTORY_ROWS = 750` constant (declare in `src/prediction/` alongside the other model constants, or in this loader module — planner's call, but must be visibly larger than 20 and imported, never re-declared, everywhere it's checked, matching `_universe_loader.py`'s single-import-source-of-truth pattern for `MIN_HISTORY_ROWS`).
- Return `{"status": "ok", "chart_df": df, "feature_frame": feature_frame, "price_series": df["Close"]}` (full frame, not just `last_row`, since walk-forward folds need every row, unlike Phase 3's single-row scoring need).

**Chokepoint-only-through-existing-functions convention:** `_universe_loader.py` never calls `yfinance` directly, only `fetch_ohlcv` from `src.data.prices`/`src.data.cache`, and never reimplements `assemble_feature_frame`. `_prediction_loader.py` must do the same — this is the single-chokepoint rule from CONTEXT.md's Established Patterns.

---

### `src/pages/search.py` (extended controller/page)

**Analog:** `src/pages/search.py` (itself — full file read, 145 lines, all extracted, no re-read needed)

**Page-thin/module-thick split + docstring convention** (lines 1-19):
```python
"""Search page (REC-04) -- free-text ticker lookup and drill-in.

``resolve_search_result(ticker, profile)`` is the testable core: it reuses
the exact same ``src.recommendation.engine.score_universe`` scoring path
...
``render_search_page()`` is the thin ``require_auth()``-gated Streamlit
wrapper around it, mirroring ``src/pages/recommendations.py``'s
page-thin/module-thick split -- all scoring math lives in
``src.recommendation.engine``, all price/feature I/O in
``src.pages._universe_loader``, and all charts/disclaimer copy in
``src.components``. This page never imports ``yfinance`` or calls
``fetch_ohlcv`` directly.
"""
```
Extend this docstring to also state: "the prediction/backtest math lives in `src.prediction.engine`, all prediction-specific I/O in `src.pages._prediction_loader`" — same rule, one more module pair.

**Testable-core / thin-render split** (`resolve_search_result` lines 51-99 vs. `render_search_page` lines 102-145): keep this exact split for the new forecast flow — add a testable `resolve_forecast_request(ticker, model, horizon, profile)`-style function (or reuse `src.prediction.engine.generate_forecast` directly if it's already sufficiently testable) that `render_search_page` merely calls and renders — do not inline model-dispatch or forecast-shape logic into the Streamlit rendering function.

**Constants-at-top-of-module copy convention** (lines 32-48): every user-facing string is a module-level constant with a `_TEMPLATE` suffix for `.format()`-based strings (`NOT_FOUND_TEMPLATE`, `INSUFFICIENT_DATA_BODY_TEMPLATE`). Apply the same convention to every string in 04-UI-SPEC.md's Copywriting Contract table — e.g. `MODEL_DROPDOWN_LABEL = "Prediction Model"`, `INSUFFICIENT_HISTORY_MESSAGE = "Not enough price history to generate a reliable forecast for this asset."`, `PROPHET_UNAVAILABLE_MESSAGE = "..."` — never inline literal strings in the render function body.

**Import block convention** (lines 21-30):
```python
import pandas as pd
import streamlit as st

from src.auth.session import require_auth
from src.components.charts import render_breakdown_bar_chart, render_price_history_chart
from src.components.disclaimer import render_disclaimer_banner
from src.data.profile import fetch_profile
from src.pages._universe_loader import fetch_scorable_row, load_universe_rows
from src.recommendation.engine import score_universe
from src.recommendation.universe import ASSET_CLASS_SECTORS, ASSET_CLASS_TICKERS, infer_asset_class
```
Extend with `from src.components.charts import build_forecast_figure, render_forecast_chart` (or whatever names land), `from src.pages._prediction_loader import fetch_prediction_data`, `from src.prediction.engine import generate_forecast` — stdlib/third-party first, then `src.*` alphabetized by module path, matching the existing ordering.

**Insufficient-data non-blocking rendering pattern (D-08 precedent)** (lines 133-137):
```python
if result["status"] == "insufficient_data":
    st.warning(INSUFFICIENT_DATA_BADGE)
    st.write(INSUFFICIENT_DATA_BODY_TEMPLATE.format(ticker=result["ticker"]))
    render_price_history_chart(result["chart_df"], key=f"chart_{result['ticker']}")
    return
```
This is the exact precedent D-08 (Phase 4) extends: chart still renders, only the score/forecast section is replaced with a warning. Reuse this shape for the new stricter `MIN_PREDICTION_HISTORY_ROWS` gate — disable/hide the model dropdown + Generate Forecast button and show `INSUFFICIENT_HISTORY_MESSAGE` in their place, while `render_price_history_chart` still runs unconditionally above it.

**`require_auth()` + `st.form` + `st.query_params` pattern** (lines 104-125): unchanged, no new pattern needed — the new model/horizon/Generate-Forecast controls are added below the existing ticker form and price chart, using plain `st.selectbox`/`st.button` (not wrapped in another `st.form`, since D-04 wants an explicit standalone button click, not a form submit).

---

### `src/components/charts.py` (extended: `build_forecast_figure`/`render_forecast_chart`)

**Analog:** `src/components/charts.py` (itself — full file read, 58 lines, all extracted, no re-read needed)

**Pure-builder / thin-renderer split convention** (lines 44-58):
```python
def build_price_history_figure(price_df: pd.DataFrame) -> go.Figure:
    """Return a single-line historical price chart from a DataFrame with
    a "Close" column."""
    scatter = go.Scatter(
        x=price_df.index,
        y=price_df["Close"],
        mode="lines",
        line_color=CHART_MARK_COLOR,
    )
    return go.Figure(data=[scatter])


def render_price_history_chart(price_df: pd.DataFrame, key: str) -> None:
    """Render the historical price line chart via st.plotly_chart."""
    st.plotly_chart(build_price_history_figure(price_df), key=key)
```
Apply the exact same two-function split for the forecast chart: `build_forecast_figure(...) -> go.Figure` (pure, independently testable, no `st` calls) + `render_forecast_chart(...) -> None` (thin `st.plotly_chart(build_forecast_figure(...), key=key)` wrapper). Reuse `build_price_history_figure` inside `build_forecast_figure` exactly as RESEARCH.md's Pattern 6 code already does (`fig = build_price_history_figure(price_df)` then `fig.add_trace(...)` three times) — do not reimplement the historical-line trace.

**Color-constant convention** (line 15): `CHART_MARK_COLOR = "#334155"` declared once at module top and reused by every `build_*_figure` function. Add `FORECAST_COLOR = "#0EA5E9"` and `CI_FILL_COLOR = "rgba(14, 165, 233, 0.2)"` (exact hex/rgba values from 04-UI-SPEC.md's Color table) the same way — module-level constants, never inlined into the trace calls.

**`key=` parameter convention** (line 56, and `search.py` call sites lines 136/141/143): every `render_*_chart` function takes an explicit `key: str` parameter, and every call site builds a per-ticker-unique key string (e.g. `key=f"chart_{result['ticker']}"`). Apply the same to `render_forecast_chart(..., key=f"forecast_{ticker}_{model}_{horizon}")` so Streamlit's widget-identity rules don't collide across model/horizon switches.

---

### `tests/test_prediction_leakage.py` (new)

**Analog:** `tests/test_features_leakage.py` (D-11 pattern, cited directly in both CONTEXT.md and RESEARCH.md Pitfall 4)

Per RESEARCH.md Pitfall 4, do not treat Phase 2's existing leakage test as covering this phase — write a new, analogous test targeting `walk_forward.make_folds` and the per-fold fit/predict loop, not `assemble_feature_frame`. Structure: (1) assert `max(train_index) < min(test_index)` for every fold; (2) synthetic-signal-injection variant — perturb a `Close` value inside one fold's test window only, refit, assert prior folds' metrics are byte-for-byte unchanged. Follow `test_features_leakage.py`'s existing test-naming/assert style (not re-read in full here to conserve budget — planner/implementer should open it directly when writing this test file, since only the pattern description, not exact line-level code, was needed for this mapping).

## Shared Patterns

### Zero-I/O package contract
**Source:** `src/recommendation/engine.py` lines 1-13 (module docstring), and the whole `src/recommendation/` package structure (`factor_scoring.py`, `profile_fit.py`, `similarity.py`, `explain.py`, `universe.py`)
**Apply to:** every file under the new `src/prediction/` package — no `streamlit`, `yfinance`, `sqlite3`, or network/LLM calls; only `pandas`/`numpy`/`xgboost`/`prophet`/`sklearn` and sibling `src.prediction` imports.

### I/O-loader-under-pages/ convention
**Source:** `src/pages/_universe_loader.py` (whole file)
**Apply to:** `src/pages/_prediction_loader.py` — same discriminated-union `{"status": ...}` return dict shape, same `try/except Exception: logger.exception(...)` guard around the single chokepoint call (`fetch_ohlcv`), same "why this lives under pages/ not the pure package" docstring justification.

### Page-thin/module-thick split + module-level string constants
**Source:** `src/pages/search.py` (whole file, both `resolve_search_result`/`render_search_page` halves)
**Apply to:** `search.py`'s Phase 4 extension — keep all forecast/backtest math in `src.prediction.engine`, keep every user-facing string (per 04-UI-SPEC.md's Copywriting Contract) as a module-level constant, keep the render function a thin sequence of `st.*` calls with no business logic.

### Pure-builder/thin-renderer chart split
**Source:** `src/components/charts.py` (whole file)
**Apply to:** `build_forecast_figure`/`render_forecast_chart` — pure `go.Figure`-returning builder + thin `st.plotly_chart` wrapper, `key=` parameter required, module-level color constants.

### Disclaimer banner reuse
**Source:** `src/components/disclaimer.py` (whole file, 26 lines)
**Apply to:** `search.py`'s extended forecast section — call the existing `render_disclaimer_banner()` (already called once per CLAUDE.md's compliance constraint); no new disclaimer component needed, and per 04-UI-SPEC.md's Copywriting Contract, add the new backtest-specific "Backtested using walk-forward validation... Hypothetical results..." caption as a *separate* `st.caption()` call near the metrics table — do not fold it into `DISCLAIMER_TEXT` itself, since that string is shared/audited across all pages (Phase 6 consolidation).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/prediction/prophet_model.py` (import-guard specifically) | service | transform | No existing module in this codebase has an optional/gracefully-degrading third-party import; RESEARCH.md Pattern 4's code is the only template. Combine with `_universe_loader.py`'s status-dict/logging conventions (see Pattern Assignments above) rather than inventing a third style. |
| D-06 "Compare all models" modal + persistent banner + toast (`search.py` extension) | controller (UI interaction) | event-driven | No existing page in this codebase uses `st.dialog`, `st.toast`, or a `st.session_state`-driven persistent banner — this is the first phase needing them. Follow RESEARCH.md Pattern 5's code directly (already vetted against the installed `streamlit==1.59.2` API via `inspect.signature`), applying the same module-level-constant-strings and `key=`-per-widget conventions established above. |

## Metadata

**Analog search scope:** `src/recommendation/`, `src/pages/`, `src/components/`, `tests/`
**Files scanned:** `src/recommendation/engine.py`, `src/pages/_universe_loader.py`, `src/pages/search.py`, `src/components/charts.py`, `src/components/disclaimer.py`, `src/recommendation/universe.py` (grep only), `src/data/cache.py` (grep only), `tests/test_features_leakage.py` (located, not opened — description sufficed)
**Pattern extraction date:** 2026-08-09
