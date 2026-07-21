---
phase: 02-investor-profile-feature-engineering-foundation
reviewed: 2026-07-20T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - supabase/migrations/20260721005033_extend_profiles_and_create_holdings.sql
  - src/features/__init__.py
  - src/features/technical.py
  - src/features/feature_frame.py
  - tests/test_features_technical.py
  - tests/test_features_leakage.py
  - src/data/profile.py
  - tests/test_profile_crud.py
  - tests/test_ticker_validation.py
  - tests/test_holdings_rls.py
  - src/pages/profile.py
  - src/app.py
findings:
  critical: 1
  warning: 3
  info: 3
  total: 7
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-07-20T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

The feature-engineering package (`src/features/`) is clean, well-scoped, and its leakage guarantees are real for the truncation-invariance test — no `center=True`, no negative shifts, no I/O imports. The migration follows established RLS/GRANT patterns correctly and matches the documented CHECK-constraint options used by the UI.

The investor-profile CRUD/UI slice (`src/data/profile.py` + `src/pages/profile.py`) has one real data-loss defect: the holdings save path can wipe a user's previously-saved holdings and leave no trace of what happened, because `upsert_holdings` deletes all existing rows before inserting the new set with no rollback, and the UI never validates that a row's `quantity` is present before handing it to that function — but the `holdings` table has `quantity numeric not null`. A user who adds a new holdings row, types only a ticker, and clicks Save will trigger exactly this path. There are also several quality/maintainability issues: form widgets without `key=` silently discard unsaved edits when a validation error fires, a documented "leakage" test that can never fail regardless of the implementation, repeated Supabase-client-scoping boilerplate that is a latent risk for a future contributor to get wrong, and a broad fail-open exception handler with no logging.

## Critical Issues

### CR-01: Holdings save can silently delete a user's holdings with no rollback and no error shown

**File:** `src/pages/profile.py:187-211`, `src/data/profile.py:118-145`

**Issue:**
`upsert_holdings` (src/data/profile.py:118-145) implements "replace all" as an unconditional `delete()` followed by an `insert()` of the new payload, with no transaction/RPC wrapping either statement:

```python
scoped_client.table("holdings").delete().eq("user_id", user_id).execute()
if rows:
    payloads = [...]
    scoped_client.table("holdings").insert(payloads).execute()
```

The caller (`src/pages/profile.py:187-203`) builds `holdings_rows` from the data-editor grid and only skips a row when its **ticker** is blank:

```python
ticker_value = row.get("ticker")
if pd.isna(ticker_value):
    continue
...
quantity_value = row.get("quantity")
quantity_value = None if pd.isna(quantity_value) else quantity_value
...
holdings_rows.append({"ticker": ticker, "quantity": quantity_value, "cost_basis": cost_basis_value})
```

There is no equivalent skip/validation for a blank `quantity`. Since `st.data_editor(num_rows="dynamic")` initializes new rows with all cells empty, a completely normal user action — add a row, type a ticker, tab away without filling in quantity, click Save — produces a row with `quantity=None`. The `holdings` table defines `quantity numeric not null` (see `supabase/migrations/20260721005033_extend_profiles_and_create_holdings.sql:36`), so the subsequent `insert()` raises a Postgres NOT NULL violation — **after** `delete()` has already removed every existing row for that user.

That exception is caught generically at `src/pages/profile.py:217-231`:

```python
try:
    upsert_profile(...)
    upsert_holdings(access_token, user_id, holdings_rows)
except Exception:
    st.error(SAVE_FAILURE_ERROR)
    return
```

The user sees only "We couldn't save your profile. Please try again." with no indication that their previously-persisted holdings are now gone, and no logging of the underlying cause. Note `upsert_profile` is called first and succeeds independently — so the profile scalar fields *are* saved while holdings are wiped, leaving the record in a partially-updated, silently-corrupted state.

**Fix:** Validate `quantity is not None` (and any other required fields) before calling `validate_ticker`/`upsert_holdings`, mirroring the existing blank-ticker skip, and surface a field-level error instead of silently dropping/crashing on the row:

```python
for _, row in edited_holdings.iterrows():
    ticker_value = row.get("ticker")
    if pd.isna(ticker_value):
        continue
    ticker = str(ticker_value).strip()
    if not ticker:
        continue
    quantity_value = row.get("quantity")
    if pd.isna(quantity_value):
        st.error(f'Quantity is required for "{ticker}".')
        _highlight_holdings_editor()
        return
    ...
```

Additionally, make `upsert_holdings` itself resilient to partial failure — e.g. validate/build all payloads and confirm they satisfy DB constraints before issuing the `delete()`, or perform the replace via a single Postgres function (`rpc(...)`) so delete+insert are atomic and a bad row can never leave the table empty.

## Warnings

### WR-01: Scalar profile-form widgets have no `key=`, so unsaved edits are silently discarded on a validation-failure rerun

**File:** `src/pages/profile.py:118-155`

**Issue:** `risk_tolerance`, `time_horizon`, `preferred_sectors`, `excluded_sectors`, the asset-type checkboxes, and `capital` are all rendered without an explicit `key=`, with their initial value/index derived from `profile = existing_profile or {}` — the *persisted* DB state fetched fresh at the top of every render (`fetch_profile`, line 104). Only `st.data_editor` for holdings is keyed (`key="holdings_editor"`, line 174), so its edits survive a rerun via `st.session_state`.

When the invalid-ticker branch fires (line 207-211: `st.error(...); _highlight_holdings_editor(); return`), the script returns without calling `upsert_profile`, but the form submission still triggers a Streamlit rerun. On that rerun, every non-keyed widget re-initializes from the still-unchanged, DB-persisted `profile` dict — silently discarding whatever the user had just selected/typed for risk tolerance, time horizon, sectors, asset types, and capital, while the holdings grid (which is keyed) correctly preserves the user's edits. This produces an inconsistent and surprising UX: the exact scenario that triggers the error (an invalid ticker) is the one guaranteed to blow away the rest of the user's unsaved form input.

**Fix:** Give each scalar widget a stable `key=` and seed its default from `st.session_state` only when not already present, e.g.:

```python
if "profile_risk_tolerance" not in st.session_state:
    st.session_state["profile_risk_tolerance"] = profile.get("risk_tolerance")
risk_tolerance_value = st.selectbox(
    "Risk Tolerance", RISK_TOLERANCE_OPTIONS, key="profile_risk_tolerance", index=...
)
```

so a validation failure elsewhere on the page never resets fields the user already filled in.

### WR-02: Repeated Supabase client-scoping boilerplate is a latent RLS-bypass risk

**File:** `src/data/profile.py:53-54, 99-100, 106-107, 132-133`

**Issue:** Every function in this module repeats the same two lines:

```python
scoped_client = create_client(get_config("SUPABASE_URL"), get_config("SUPABASE_ANON_KEY"))
scoped_client.postgrest.auth(access_token)
```

This is the *only* thing that makes each request RLS-enforced as the caller rather than an anonymous client. Because it's copy-pasted four times rather than centralized, a future function added to this module (or a future edit to one of these four) can trivially omit the `.postgrest.auth(access_token)` call and silently fall back to unscoped anon-key access — a correctness bug that would only surface as an unexpected RLS "zero rows" result or, in a worse case involving a different key, a real authorization gap. The module's own docstring (lines 1-12) stresses how load-bearing this discipline is, which is itself a signal it should be enforced structurally, not by convention.

**Fix:** Extract a single helper (mirroring `tests/test_holdings_rls.py`'s own `_scoped_client`):

```python
def _scoped_client(access_token: str):
    client = create_client(get_config("SUPABASE_URL"), get_config("SUPABASE_ANON_KEY"))
    client.postgrest.auth(access_token)
    return client
```

and use it in `fetch_profile`, `upsert_profile`, `fetch_holdings`, and `upsert_holdings`.

### WR-03: Synthetic future-signal leakage test can never fail, regardless of implementation

**File:** `tests/test_features_leakage.py:37-51`

**Issue:**
```python
df["cheat_future_close"] = df.loc[future_date, "Close"]
features = assemble_feature_frame(df)
assert "cheat_future_close" not in features.columns.tolist() or (
    features.loc[: df.index[79], "cheat_future_close"].isna().all()
)
```
`assemble_feature_frame` (src/features/feature_frame.py:15-34) only ever reads `df["Close"]` (via the four `technical.*` functions) and always returns a fresh `DataFrame` containing exactly `["returns", "volatility_20", "sma_20", "rsi_14"]`. It never copies through or references arbitrary input columns, so `"cheat_future_close"` can **never** appear in `features.columns` — the first disjunct of the `or` is unconditionally `True` for any implementation of this module, including a hypothetically broken one. This test therefore provides no actual leakage protection beyond what `test_truncation_invariance_no_future_data_changes_past_features` in the same file already proves; it reads as a meaningful independent guard (per its own docstring: "via two independent checks") but is not one, which risks giving false confidence that D-11 has two layers of proof when it has one.

**Fix:** Either remove this test (truncation invariance already covers D-11), or rewrite it to actually exercise the injected future value through the computation path it claims to guard — e.g. perturb `df["Close"]` at `future_date` itself and assert rows `< future_date` are unchanged, which is a genuine second angle on the same invariant rather than a column-membership check that is vacuously true by construction.

## Info

### IN-01: `validate_ticker`'s broad fail-open `except` swallows all errors with no logging

**File:** `src/data/profile.py:165-169`

**Issue:** `except Exception: return True` is intentionally documented as a fail-open policy for transient data-layer failures, but as written it also silently swallows genuine programming errors inside `fetch_ohlcv` (e.g. a `TypeError`/`AttributeError` from a regression elsewhere) with zero logging, making such regressions invisible in production.

**Fix:** Log the exception before returning, e.g. `except Exception as exc: logging.getLogger(__name__).warning("validate_ticker fetch failed for %s: %s", ticker, exc); return True`, so fail-open behavior is preserved but debuggable.

### IN-02: `upsert_profile` always overwrites all six fields — a footgun for future callers

**File:** `src/data/profile.py:67-101`

**Issue:** The payload dict is built from all six keyword arguments unconditionally, defaulting any omitted one to `None`. This is safe today because the single call site (`src/pages/profile.py:217-227`) always passes every field, but the function itself has no partial-update support — a future caller that only wants to patch one field (e.g. just `capital`) would silently NULL out the other five.

**Fix:** Document this constraint prominently in the signature/docstring (already partially done), or accept an explicit dict of only the fields to change and build the payload from `{k: v for k, v in fields.items()}` to support partial updates safely.

### IN-03: No validation prevents a sector from being both preferred and excluded simultaneously

**File:** `src/pages/profile.py:132-141`

**Issue:** `preferred_sectors_value` and `excluded_sectors_value` are independent multiselects over the same `SECTORS` list with no mutual-exclusivity check, so a user can select "Tech" in both lists and save successfully — a contradictory profile state with no feedback.

**Fix:** Add a lightweight validation before save: `overlap = set(preferred_sectors_value) & set(excluded_sectors_value)`, and surface an `st.error` listing the conflicting sectors if non-empty.

---

_Reviewed: 2026-07-20T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
