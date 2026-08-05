# Phase 3: Deterministic Recommendation Engine - Pattern Map

**Mapped:** 2026-08-04
**Files analyzed:** 10 (8 new modules + 2 pages; `app.py` modified in place)
**Analogs found:** 10 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/recommendation/universe.py` | config | static-data | `src/pages/profile.py` (module-level `SECTORS`/`ASSET_TYPE_OPTIONS` constants, lines 58-72) | role-match |
| `src/recommendation/factor_scoring.py` | utility (pure transform) | transform | `src/features/technical.py` | exact |
| `src/recommendation/similarity.py` | utility (pure transform) | transform | `src/features/technical.py` | exact |
| `src/recommendation/profile_fit.py` | utility (pure transform) | transform | `src/features/technical.py` | exact |
| `src/recommendation/explain.py` | utility (pure transform) | transform | `src/features/technical.py` | exact |
| `src/recommendation/engine.py` | service (orchestrator) | batch/transform | `src/features/feature_frame.py` (`assemble_feature_frame` orchestrates `technical.py` functions) | exact |
| `src/pages/recommendations.py` | route/page | request-response | `src/pages/home.py` (thin, `require_auth()`-first page) | role-match |
| `src/pages/search.py` | route/page | request-response | `src/pages/profile.py` (page-thin/module-thick split, calls a CRUD chokepoint) | role-match |
| `src/app.py` (modified) | config/route registration | request-response | itself (existing `st.navigation` wiring) | exact |
| `tests/test_recommendation_*.py` (5 files) | test | transform | `tests/test_features_technical.py` | exact |

## Pattern Assignments

### `src/recommendation/universe.py` (config, static-data)

**Analog:** `src/pages/profile.py` lines 58-72 (module-level constant lists) + RESEARCH.md's own "Curated universe structure" Code Example (already-designed, not from existing codebase — use as-is).

**Constant-list pattern to copy** (`src/pages/profile.py` lines 60-72):
```python
SECTORS = [
    "Tech",
    "Healthcare",
    "Financials",
    ...
]
ASSET_TYPE_OPTIONS = ["Stocks", "ETFs", "Crypto", "Gold", "Forex"]
```
Sector strings in `universe.py`'s `STOCK_UNIVERSE` **must match `SECTORS` in `src/pages/profile.py` exactly** (same casing/spelling) so `profile_fit.py`'s sector include/exclude logic can do a direct string match with no normalization step. `ASSET_TYPE_OPTIONS` values (`"Stocks"`, `"ETFs"`, `"Crypto"`, `"Gold"`, `"Forex"`) are the exact `asset_class` tag vocabulary `universe.py` must use per asset.

No I/O in this file — pure static data, mirrors the "config, not fetched" role RESEARCH.md assigns it. Use RESEARCH.md's `STOCK_UNIVERSE`/`ETF_UNIVERSE`/`CRYPTO_UNIVERSE`/`GOLD_UNIVERSE`/`FOREX_UNIVERSE` code block verbatim as the starting point (already vetted in 03-RESEARCH.md's "Code Examples" section).

---

### `src/recommendation/factor_scoring.py`, `similarity.py`, `profile_fit.py`, `explain.py` (utility, pure transform)

**Analog:** `src/features/technical.py` (entire file, 61 lines)

**Module docstring pattern to copy** (`src/features/technical.py` lines 1-18) — every new `recommendation/` module must open with an equivalent docstring stating: pure functions, no I/O, imports only `pandas`/`numpy`, never fetches its own data, never imports `streamlit`/`yfinance`/`sqlite3`:
```python
"""Pure, zero-I/O point-in-time technical/factor feature functions.

Every function here takes an already-fetched OHLCV ``DataFrame``
... and returns a ``pandas.Series`` aligned to ``df.index``.
...
This module imports ``pandas`` and ``pandas_ta_classic`` only — no
``streamlit``, no ``yfinance``, no ``sqlite3``. It never fetches its own
data.
"""

import pandas as pd
import pandas_ta_classic as ta
```

**Core function-per-transform pattern** (lines 24-39) — one small, independently-testable function per computation, each taking the already-assembled data and returning a plain pandas object, never mutating input in place:
```python
def compute_returns(df: pd.DataFrame) -> pd.Series:
    """Simple percent-change return of the close price.
    ...
    """
    return df["Close"].pct_change()


def compute_volatility(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Rolling standard deviation of returns over ``window`` bars.
    ...
    """
    return compute_returns(df).rolling(window, center=False).std()
```
Apply this same "one narrow pure function, explicit docstring stating the exact math/contract" style to:
- `factor_scoring.py`: `compute_momentum_percentile(universe_df)`, `compute_stability_percentile(universe_df)` — each using `groupby("asset_class").transform(...)` per RESEARCH.md Pattern 2.
- `similarity.py`: `cosine_similarity(a, b)`, `similarity_score(asset_vector, risk_tolerance)` — per RESEARCH.md Pattern 3's code block (already-designed target).
- `profile_fit.py`: `compute_profile_fit(asset_row, profile)` — rule-based checklist scorer per RESEARCH.md Pattern 4.
- `explain.py`: `explain(top_factors, risk_tolerance)` — per RESEARCH.md Pattern 5's code block; must derive `top_factors` from the exact same `sub_scores` dict `engine.py` returns (traceability requirement, D-06).

**No error-handling/try-except pattern needed** — `technical.py` has none because it is pure/zero-I/O and trusts its DataFrame input; the new `recommendation/` modules should follow the same discipline (no defensive try/except inside pure scoring functions — guard conditions like "insufficient history" or "group size < 3" belong in `engine.py`'s orchestration layer, per RESEARCH.md Pitfall 2/4, not scattered through each utility function).

---

### `src/recommendation/engine.py` (service, batch/transform orchestrator)

**Analog:** `src/features/feature_frame.py` (33 lines)

**Orchestration pattern to copy** (entire file, lines 1-34):
```python
"""The single shared feature-assembly entry point.

``assemble_feature_frame`` is the one function this phase's tests and a
future backtest harness / live inference call — no duplicated
feature-computation logic exists elsewhere ... It calls only
``src.features.technical`` functions; it never reimplements any
rolling-window logic inline.
"""

import pandas as pd

from src.features import technical


def assemble_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Assemble the point-in-time feature frame for a single asset.
    ...
    """
    features = pd.DataFrame(index=df.index)
    features["returns"] = technical.compute_returns(df)
    features["volatility_20"] = technical.compute_volatility(df, window=20)
    features["sma_20"] = technical.compute_sma(df, window=20)
    features["rsi_14"] = technical.compute_rsi(df, window=14)
    return features
```
`engine.py` follows the identical shape: a single public orchestration function (e.g. `build_recommendations(profile, feature_frames_by_ticker)`) that calls only `recommendation.factor_scoring`, `recommendation.similarity`, `recommendation.profile_fit`, `recommendation.explain` — never reimplementing any of their math inline, and staying zero-I/O itself (the caller, i.e. the page, is responsible for the `fetch_ohlcv`/`assemble_feature_frame` calls per asset before invoking `engine.py`). This mirrors `feature_frame.py`'s exact "assemble from sub-modules, no duplicated logic, no I/O" contract, extended with RESEARCH.md Pattern 1's composite-score dict shape (`{"composite_score": ..., "sub_scores": {...}, "weights": {...}}`) and D-05's top-N-per-class grouping.

---

### `src/pages/recommendations.py` (route/page, request-response)

**Analog:** `src/pages/home.py` (26 lines) for the thin-page shape; `src/pages/profile.py` for the "page orchestrates, module does the work" split when the ranked list needs profile data.

**Auth-gate pattern to copy** (`src/pages/home.py` lines 14-16):
```python
def render_home_page() -> None:
    """Render the require_auth()-gated placeholder home page."""
    require_auth()

    st.title("You're in")
    ...
```
`recommendations.py`'s `render_recommendations_page()` must call `require_auth()` first and only, exactly like both `home.py` and `profile.py` — no inline auth logic (per this codebase's D-04 auth pattern, established Phase 1, reaffirmed by CONTEXT.md's "Established Patterns" section for this phase).

**Fresh-fetch-per-render pattern to copy** (`src/pages/profile.py` lines 103-106):
```python
    user = require_auth()
    access_token = st.session_state["access_token"]
    user_id = user.id

    existing_profile = fetch_profile(access_token, user_id)
```
`recommendations.py` fetches the profile the same way (via `src.data.profile.fetch_profile`), then passes it into `recommendation.engine.build_recommendations(...)` — never re-implementing a Supabase read inline (mirrors `profile.py`'s "this page never talks to Supabase directly" discipline, docstring lines 13-14).

**Page-thin/module-thick split** — per `profile.py`'s docstring (lines 21-25): this page captures/renders only; all scoring math lives in `src/recommendation/`, never inline in the page module (matches ARCHITECTURE.md's explicit design goal referenced in CONTEXT.md's Integration Points).

---

### `src/pages/search.py` (route/page, request-response)

**Analog:** `src/pages/profile.py` (validation-and-chokepoint-call pattern, specifically `validate_ticker`'s usage, lines 233-239) + `src/data/profile.py`'s `validate_ticker` function itself (lines 179-200) as the direct analog for "call `fetch_ohlcv`, check empty vs. exception."

**Ticker-fetch-and-validate pattern to copy** (`src/data/profile.py` lines 196-200):
```python
    try:
        df, _status = fetch_ohlcv(ticker, period="5d")
    except Exception:
        return True
    return not df.empty
```
`search.py`'s free-text search handler follows the same shape: call `fetch_ohlcv(ticker)` (imported from `src.data.prices`, never `src.data.cache` or a direct `yfinance` import — the single-chokepoint rule this codebase enforces everywhere), branch on empty-DataFrame vs. exception vs. success, then apply D-08's specific "insufficient data for scoring" branch (chart-only render) instead of `validate_ticker`'s boolean fail-open return.

**Import pattern to copy** (`src/data/profile.py` line 41, `src/data/prices.py` lines 9-11):
```python
from src.data.prices import fetch_ohlcv
```
`search.py` must import `fetch_ohlcv` from `src.data.prices` (the public entry point), not `src.data.cache` directly — matches `src/data/prices.py`'s own docstring ("Later phases' recommendation/prediction code must import `fetch_ohlcv` from here").

**Auth-gate + page-thin pattern:** same as `recommendations.py` above — `require_auth()` first and only.

---

### `src/app.py` (modified — route registration)

**Analog:** itself, existing pattern (lines 25-38).

**Page-registration pattern to copy**:
```python
from src.pages.home import render_home_page  # noqa: E402
from src.pages.login import render_login_page  # noqa: E402
from src.pages.profile import render_profile_page  # noqa: E402

login_page = st.Page(render_login_page, title="Log In", url_path="login")
home_page = st.Page(render_home_page, title="Home", url_path="home", default=True)
profile_page = st.Page(render_profile_page, title="Investor Profile", url_path="profile")

if st.session_state.get("logged_in"):
    pg = st.navigation({"Home": [home_page], "Profile": [profile_page]})
else:
    pg = st.navigation([login_page])
```
Add `render_recommendations_page`/`render_search_page` imports (with the same `# noqa: E402` comment, since they come after the `sys.path` insert block), construct `st.Page(...)` entries with `url_path="recommendations"`/`url_path="search"`, and add them to the `{"Home": [...], "Profile": [...]}` dict passed to `st.navigation` inside the existing `if st.session_state.get("logged_in"):` branch — never registered in the logged-out branch.

---

### `tests/test_recommendation_*.py` (5 new test files)

**Analog:** `tests/test_features_technical.py` (80 lines)

**Synthetic-data test pattern to copy** (lines 1-32):
```python
"""Tests for src/features/technical.py and feature_frame.py (PROFILE-01).

All tests operate on a small deterministic synthetic OHLCV DataFrame --
no network calls, no yfinance, no Streamlit. src/features/ is a pure,
zero-I/O module: these tests exercise that contract directly.
"""

import numpy as np
import pandas as pd
import pytest

from src.features.feature_frame import assemble_feature_frame
from src.features.technical import (
    compute_returns,
    compute_rsi,
    compute_sma,
    compute_volatility,
)


def _sample_ohlcv(n_rows: int = 40) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n_rows, freq="D")
    close = pd.Series(...)
    return pd.DataFrame({"Open": close, "High": close + 1, "Low": close - 1, "Close": close})
```
Every `tests/test_recommendation_*.py` file should follow this exact shape: a module docstring stating "no network calls, no yfinance, no Streamlit," a small `_sample_*` synthetic-data builder helper local to the test file (e.g. `_synthetic_universe_df()` building a multi-asset-class DataFrame with deliberately skewed crypto-vs-gold volatility, for Pitfall 1's regression test), then one `def test_...():` per behavior asserted directly against plain pandas/numpy equality (`pd.testing.assert_series_equal`, `np.testing.assert_allclose`) — no mocking framework needed for the pure-function tests. Only `test_recommendation_search.py` needs `unittest.mock.patch` (see `tests/test_ticker_validation.py` for that pattern, not reproduced here as it's a smaller/secondary analog).

## Shared Patterns

### Auth gate
**Source:** `src/auth/session.py` `require_auth()`, used identically in `src/pages/home.py` line 16 and `src/pages/profile.py` line 99.
**Apply to:** `src/pages/recommendations.py`, `src/pages/search.py` — call first, and only, no inline auth logic.
```python
def render_home_page() -> None:
    require_auth()
    ...
```

### Single data chokepoint
**Source:** `src/data/prices.py` (entire file) — `fetch_ohlcv` is the only sanctioned yfinance entry point; `src/data/cache.py` is the only module permitted to import `yfinance` directly.
**Apply to:** `src/pages/search.py` (D-07 direct lookup), and indirectly `src/recommendation/engine.py`'s caller (the `recommendations.py` page loops the curated universe through `fetch_ohlcv` + `assemble_feature_frame` before calling `engine.py`, which itself stays I/O-free).
```python
from src.data.cache import fetch_ohlcv
__all__ = ["fetch_ohlcv"]
```

### Zero-I/O pure-function module discipline
**Source:** `src/features/technical.py` module docstring (lines 1-18) and `src/features/feature_frame.py` (lines 1-8).
**Apply to:** every file in `src/recommendation/` except the two pages — no `streamlit`, `yfinance`, or Supabase imports; only `pandas`/`numpy` and sibling `recommendation.*` modules.

### Feature assembly (already built, must be reused not reimplemented)
**Source:** `src/features/feature_frame.py::assemble_feature_frame`, `src/features/technical.py` (`compute_returns`, `compute_volatility`, `compute_sma`, `compute_rsi`).
**Apply to:** both `recommendations.py` and `search.py` — call `assemble_feature_frame(df)` on the `fetch_ohlcv` result, never reimplement rolling-window/RSI/SMA math inside `recommendation/`.

### Profile CRUD chokepoint
**Source:** `src/data/profile.py::fetch_profile` (lines 64-83), used in `src/pages/profile.py` lines 105-106.
**Apply to:** `src/pages/recommendations.py` — read the signed-in user's profile the same way (`fetch_profile(access_token, user_id)`), never a direct Supabase call from the page.

## No Analog Found

None — every new/modified file for this phase has a clear, closely-matching existing analog in `src/features/` (pure-function style), `src/pages/` (page-thin/module-thick + auth-gate style), `src/data/` (single-chokepoint style), or `tests/test_features_technical.py` (synthetic-data pure-function test style). This phase is explicitly designed (per RESEARCH.md) to extend already-established codebase patterns rather than introduce new ones.

## Metadata

**Analog search scope:** `src/features/`, `src/pages/`, `src/data/`, `src/auth/`, `tests/` (entire repo — small codebase, exhaustive read feasible)
**Files scanned:** `src/features/technical.py`, `src/features/feature_frame.py`, `src/data/prices.py`, `src/data/profile.py`, `src/data/cache.py` (referenced, not fully read — chokepoint contract already documented in `prices.py`), `src/pages/profile.py`, `src/pages/home.py`, `src/auth/session.py`, `src/app.py`, `tests/test_features_technical.py`
**Pattern extraction date:** 2026-08-04
