---
phase: 02-investor-profile-feature-engineering-foundation
plan: 02
subsystem: features
tags: [pandas-ta-classic, technical-indicators, leakage-safety, point-in-time]

# Dependency graph
requires:
  - phase: 01-foundation-data-layer-caching-auth
    provides: "src/data/prices.py's fetch_ohlcv() as the future caller of assemble_feature_frame(); src/data/prices.py's zero-I/O module-boundary discipline pattern reused here"
provides:
  - "src/features/technical.py: compute_returns(df), compute_volatility(df, window), compute_sma(df, window), compute_rsi(df, window) — pure functions, DataFrame in, Series out, no I/O"
  - "src/features/feature_frame.py: assemble_feature_frame(df) -> DataFrame — the single shared entry point Phase 3/4 will import"
  - "pandas-ta-classic==0.6.52 and pandas==2.3.3 pinned in requirements.txt"
affects: [phase-03-recommendation-engine, phase-04-prediction-backtesting]

# Tech tracking
tech-stack:
  added:
    - "pandas-ta-classic==0.6.52 (importable as pandas_ta_classic, not pandas_ta)"
    - "pandas==2.3.3 (pinned exact version, already satisfied)"
  patterns:
    - "Zero-I/O feature module boundary (src/features/) mirroring src/data/prices.py's discipline — functions take an already-fetched DataFrame, never fetch their own data"
    - "pandas_ta_classic functional API called with a positional Series argument (ta.sma(df[\"Close\"], length=window)) rather than the df.ta DataFrame accessor, to avoid column-name auto-detection ambiguity"
    - "Leakage smoke test pattern: truncation invariance + synthetic future-signal injection, reusable for any future point-in-time feature addition"

key-files:
  created:
    - src/features/__init__.py
    - src/features/technical.py
    - src/features/feature_frame.py
    - tests/test_features_technical.py
    - tests/test_features_leakage.py
  modified:
    - requirements.txt

key-decisions:
  - "Task 1 human-verify checkpoint approved: pandas-ta-classic confirmed as a genuine pandas-ta fork-continuation (not a namesquat) before install"
  - "pandas_ta_classic's functional API (ta.sma/ta.rsi called positionally on a Series) used instead of the df.ta accessor, per plan's stated preference"
  - "compute_sma's output verified to exactly match a plain df[\"Close\"].rolling(window, center=False).mean() (zero float divergence), confirming pandas_ta_classic's SMA has no hidden smoothing/adjustment"

patterns-established:
  - "Pattern: any new src/features/ function must be provably point-in-time-safe via the same two-part leakage test shape (truncation invariance + future-signal injection), not just unit-tested for correctness"

requirements-completed: [PROFILE-01]

coverage:
  - id: D1
    description: "src/features/technical.py provides compute_returns/compute_volatility/compute_sma/compute_rsi as pure, zero-I/O functions using only non-centered rolling windows"
    requirement: "PROFILE-01"
    verification:
      - kind: unit
        ref: "pytest tests/test_features_technical.py -q -> 8 passed"
        status: pass
      - kind: structural
        ref: "grep -c center=True / .shift(- / import streamlit against src/features/technical.py and feature_frame.py -> zero matches in all three"
        status: pass
    human_judgment: false
  - id: D2
    description: "assemble_feature_frame(df) assembles returns/volatility_20/sma_20/rsi_14 into one DataFrame aligned to df.index, calling only technical.py functions"
    requirement: "PROFILE-01"
    verification:
      - kind: unit
        ref: "test_assemble_feature_frame_has_exact_expected_columns_and_index, test_assemble_feature_frame_truncation_invariance -> pass"
        status: pass
    human_judgment: false
  - id: D3
    description: "Leakage smoke test proves no future information reaches a past feature value, via truncation invariance and synthetic future-signal injection"
    requirement: "PROFILE-01"
    verification:
      - kind: unit
        ref: "pytest tests/test_features_leakage.py -q -> 2 passed"
        status: pass
    human_judgment: false
  - id: D4
    description: "pandas-ta-classic==0.6.52 and pandas==2.3.3 installed and pinned in requirements.txt alongside Phase 1's five existing entries, unchanged"
    requirement: "PROFILE-01"
    verification:
      - kind: integration
        ref: "grep -c pandas-ta-classic==0.6.52 / pandas==2.3.3 / streamlit==1.59.2 requirements.txt -> 1/1/1; python -c \"import pandas_ta_classic\" -> exit 0"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-21
status: complete
---

# Phase 2 Plan 2: Feature Engineering Foundation Summary

**Built `src/features/` — a pure, zero-I/O technical-feature pipeline (`compute_returns`/`compute_volatility`/`compute_sma`/`compute_rsi` + `assemble_feature_frame`) proven point-in-time-safe by a leakage smoke test, after a human-verify checkpoint confirmed `pandas-ta-classic`'s package legitimacy.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 3 completed (Task 1 checkpoint approval, Task 2 install/pin, Task 3 implementation + tests)
- **Files modified:** 6 (1 modified, 5 created)

## Accomplishments
- Task 1 blocking human-verify checkpoint: user confirmed `pandas-ta-classic` is a genuine `pandas-ta` fork-continuation (real commit history, maintained README, correct package name) before any install ran.
- `pandas-ta-classic==0.6.52` and `pandas==2.3.3` installed and pinned in `requirements.txt`, appended after Phase 1's five existing lines, none reordered or removed.
- `src/features/technical.py`: four pure functions (`compute_returns`, `compute_volatility`, `compute_sma`, `compute_rsi`), all zero-I/O, all using non-centered rolling windows, calling `pandas_ta_classic`'s functional API (`ta.sma`/`ta.rsi` on a positional `Series`) rather than the `df.ta` accessor.
- `src/features/feature_frame.py`: `assemble_feature_frame(df)` as the single shared entry point, assembling `"returns"`/`"volatility_20"`/`"sma_20"`/`"rsi_14"` from `technical.py` calls only.
- `tests/test_features_technical.py` (8 tests) and `tests/test_features_leakage.py` (2 tests) — all passing, including exact-match verification that `compute_sma` equals a plain `rolling(window, center=False).mean()` with zero float divergence, and RSI values bounded to `[0, 100]`.
- Full project test suite (40 tests) still green after this plan's changes — no regressions in Phase 1's auth/cache/RLS coverage.

## Task Commits

Each task was committed atomically:

1. **Task 1: [BLOCKING] Verify pandas-ta-classic package legitimacy** - checkpoint approval only, no file changes, no commit
2. **Task 2: Install and pin pandas-ta-classic + pandas** - `5840459` (feat)
3. **Task 3: Point-in-time technical features + leakage smoke test** - `6720d2d` (feat)

## Files Created/Modified
- `requirements.txt` - Appended `pandas-ta-classic==0.6.52` and `pandas==2.3.3` after Phase 1's five existing lines
- `src/features/__init__.py` - Package marker documenting the zero-I/O module boundary; re-exports `assemble_feature_frame`
- `src/features/technical.py` - `compute_returns`, `compute_volatility`, `compute_sma`, `compute_rsi` — pure functions, no I/O, no centered windows
- `src/features/feature_frame.py` - `assemble_feature_frame(df)` calling only `technical.py` functions
- `tests/test_features_technical.py` - Unit coverage for all four functions plus `assemble_feature_frame`'s column/index contract and a structural center=True/shift(-)/streamlit-import guard
- `tests/test_features_leakage.py` - Truncation-invariance and synthetic-future-signal-injection leakage smoke tests

## Decisions Made
- Used `pandas_ta_classic`'s functional API (`ta.sma(df["Close"], length=window)`) instead of the `df.ta` accessor, per the plan's stated preference to sidestep column-name auto-detection ambiguity.
- Verified `compute_sma`'s output against a plain rolling mean with an exact-equality check (not just a range/shape check) before relying on it — confirms `pandas_ta_classic`'s SMA has no hidden adjustment/smoothing that would silently diverge from the documented "plain rolling mean" contract.

## Deviations from Plan

**Import name correction (RESEARCH.md's own [ASSUMED] flag confirmed as wrong):** 02-02-PLAN.md's Task 2 acceptance criteria and verify command both assumed `python -c "import pandas_ta"` would succeed. The installed `pandas-ta-classic==0.6.52` package's actual importable module name is `pandas_ta_classic` (confirmed via `pip show -f pandas-ta-classic`'s file listing — `pandas_ta_classic/__init__.py`, not `pandas_ta/`). `import pandas_ta` fails with `ModuleNotFoundError` against the real installed package. All code (`technical.py`) and the actual verify check run in this plan use `import pandas_ta_classic` instead. This was flagged as unverified in 02-RESEARCH.md itself ("[ASSUMED — not verified against Context7/official docs this session]" and "verify exact column-naming output ... against the installed 0.6.52 package during implementation, not just this research") — this plan's implementation is the verification, and it surfaced the naming discrepancy as expected.

No other deviations — Task 3's behavior contract (four functions' signatures, `assemble_feature_frame`'s exact four columns, leakage test shapes) was implemented exactly as specified.

## Issues Encountered
Docstring prose in `technical.py` initially contained the literal substring `"center=True"` (describing what the module deliberately avoids), which tripped both a self-written structural test and would have tripped the plan's own `grep -q "center=True"` verify command — a false positive from prose, not an actual centered-window bug. Reworded the docstrings to describe the same guarantee without using the literal flagged substring, then re-verified the grep-based checks pass cleanly.

## User Setup Required

None - `pandas-ta-classic` and `pandas` are Python packages installed via `pip`/`requirements.txt`, no external service configuration.

## Next Phase Readiness
`assemble_feature_frame(df)` is available, tested, and proven leakage-safe for Phase 3 (recommendation engine) and Phase 4 (prediction/backtesting) to import directly against real `fetch_ohlcv()` output — no rework anticipated. Plan 02-03 (profile/holdings CRUD) and Plan 02-04 (profile UI) are unaffected by and do not depend on this plan's work (per 02-CONTEXT.md's Phase Boundary, `src/pages/profile.py` must not import from `src.features`). No blockers identified.

---
*Phase: 02-investor-profile-feature-engineering-foundation*
*Completed: 2026-07-21*

## Self-Check: PASSED

- FOUND: src/features/technical.py
- FOUND: src/features/feature_frame.py
- FOUND: src/features/__init__.py
- FOUND: tests/test_features_technical.py
- FOUND: tests/test_features_leakage.py
- FOUND: commit 5840459
- FOUND: commit 6720d2d
