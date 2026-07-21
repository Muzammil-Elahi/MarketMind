"""Single chokepoint for all ``profiles``/``holdings`` Supabase CRUD, plus
ticker validation for the investor-profile builder (PROFILE-01/PROFILE-02).

Every function here builds a fresh, short-lived ``create_client(...)`` per
call and attaches the caller's ``access_token`` to it before making exactly
one request -- the same discipline ``src/auth/session.py``'s
``_touch_last_login`` already established in Phase 1 -- so every read/write
is RLS-enforced as the signed-in caller, never through the process-wide
shared client used elsewhere in this codebase for anonymous/stateless reads.
The scoped client built in each function below goes out of scope
immediately after its single call; it is never stored in
``st.session_state`` or any cached/global object.

``upsert_profile`` always issues an ``UPDATE`` against ``profiles`` --
never an ``INSERT``/``upsert`` -- because ``public.profiles`` has no
client-facing INSERT policy (Phase 1's ``handle_new_user()`` trigger is the
only insert path, and a row always already exists for every signed-up user
by the time this module is ever called).

``upsert_holdings`` replaces all of a user's ``holdings`` rows on every save
(delete-then-insert) and builds each inserted row's payload explicitly from
``ticker``/``quantity``/``cost_basis`` -- never a raw pass-through of the
caller-supplied row dict -- so an unexpected extra key (e.g. a spoofed
``user_id``) in a row can never override the server-supplied ownership
value (T-02-04 mass-assignment mitigation).

``validate_ticker`` flags a ticker as invalid only when ``fetch_ohlcv``
succeeds but returns an empty DataFrame (Pitfall 1: yfinance returns an
empty DataFrame, not an exception, for an unrecognized/delisted ticker). A
genuine network/API exception is treated as inconclusive and fails open
(returns ``True``), since a transient data-layer failure is not evidence
the ticker symbol itself is wrong.

No function in this module is wrapped in a Streamlit caching decorator
(D-13 -- profile reads are always fetched fresh).
"""

from supabase import create_client

from src.config import get_config
from src.data.prices import fetch_ohlcv


def _scoped_client(access_token: str):
    """Build a fresh anon-key Supabase client scoped to one caller's access
    token (WR-02).

    This is the *only* thing that makes a request RLS-enforced as the
    signed-in caller rather than an anonymous client -- every function
    below must go through this helper rather than repeating
    ``create_client(...)`` + ``.postgrest.auth(access_token)`` inline, so a
    future function added to this module can never accidentally omit the
    ``.postgrest.auth(access_token)`` call and silently fall back to
    unscoped anon-key access. Mirrors ``tests/test_holdings_rls.py``'s own
    ``_scoped_client`` helper. The returned client goes out of scope
    immediately after its single call; it is never stored in
    ``st.session_state`` or any cached/global object.
    """
    client = create_client(get_config("SUPABASE_URL"), get_config("SUPABASE_ANON_KEY"))
    client.postgrest.auth(access_token)
    return client


def fetch_profile(access_token: str, user_id: str) -> dict | None:
    """Fetch the ``profiles`` scalar fields for ``user_id``.

    Returns ``None`` if no row is found (should not normally happen post
    signup, since ``handle_new_user()``'s trigger always provisions a row --
    but a scoped client honoring RLS could still legitimately see zero rows
    if called with a mismatched token/user_id pair). Not cached -- always
    fetches fresh from Supabase (D-13).
    """
    scoped_client = _scoped_client(access_token)
    result = (
        scoped_client.table("profiles")
        .select(
            "risk_tolerance, time_horizon, preferred_sectors, excluded_sectors, "
            "preferred_asset_types, capital"
        )
        .eq("user_id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None


def upsert_profile(
    access_token: str,
    user_id: str,
    *,
    risk_tolerance=None,
    time_horizon=None,
    preferred_sectors=None,
    excluded_sectors=None,
    preferred_asset_types=None,
    capital=None,
) -> None:
    """Save the six investor-profile scalar fields for ``user_id``.

    Always an ``UPDATE`` -- never an upsert or insert call -- since
    ``public.profiles`` has no client-facing INSERT policy; the row always
    already exists by the time this is called. Named keyword arguments make
    mass-assignment structurally impossible here: the payload is built from
    exactly these six keys, nothing else, regardless of what a caller might
    otherwise have tried to pass through.

    Idempotent by construction: calling this twice in a row with identical
    kwargs always UPDATEs the same single row (``profiles.user_id`` is the
    primary key), never creating a second row.
    """
    payload = {
        "risk_tolerance": risk_tolerance,
        "time_horizon": time_horizon,
        "preferred_sectors": preferred_sectors,
        "excluded_sectors": excluded_sectors,
        "preferred_asset_types": preferred_asset_types,
        "capital": capital,
    }
    scoped_client = _scoped_client(access_token)
    scoped_client.table("profiles").update(payload).eq("user_id", user_id).execute()


def fetch_holdings(access_token: str, user_id: str) -> list[dict]:
    """Fetch all ``holdings`` rows owned by ``user_id``, oldest first."""
    scoped_client = _scoped_client(access_token)
    result = (
        scoped_client.table("holdings")
        .select("id, ticker, quantity, cost_basis")
        .eq("user_id", user_id)
        .order("created_at")
        .execute()
    )
    return result.data


def upsert_holdings(access_token: str, user_id: str, rows: list[dict]) -> None:
    """Replace all of ``user_id``'s ``holdings`` rows with ``rows``.

    Replace-all-on-save semantics: delete every existing row for this
    user_id, then insert the current grid state (no uniqueness constraint
    on ticker, so this is safe -- matches RESEARCH.md's recommendation).

    Each inserted row's payload is built explicitly from
    ``row["ticker"]``/``row["quantity"]``/``row.get("cost_basis")`` --
    deliberately not forwarding the entire input row dict as-is -- so a
    caller-supplied row containing an unexpected extra key (for example a
    different ``user_id`` value) can never override the server-supplied
    ownership value (T-02-04).

    CR-01: every payload is built AND validated against known
    ``not null`` DB constraints (``quantity``) *before* the ``delete()`` is
    issued. The caller (``src/pages/profile.py``) already guards against a
    blank ``quantity`` reaching this function, but this module is the CRUD
    chokepoint -- validating here too means a future caller can never
    reintroduce the delete-then-crash-with-no-rollback failure mode by
    skipping that UI-level check.
    """
    payloads = [
        {
            "user_id": user_id,
            "ticker": row["ticker"],
            "quantity": row["quantity"],
            "cost_basis": row.get("cost_basis"),
        }
        for row in rows
    ]
    for payload in payloads:
        if payload["quantity"] is None:
            raise ValueError(
                f'quantity is required for ticker "{payload["ticker"]}"; '
                "refusing to replace holdings with an invalid row"
            )

    scoped_client = _scoped_client(access_token)
    scoped_client.table("holdings").delete().eq("user_id", user_id).execute()
    if payloads:
        scoped_client.table("holdings").insert(payloads).execute()


def validate_ticker(ticker: str) -> bool:
    """Validate a ticker symbol against yfinance for D-08 form-submit checks.

    Calls ``fetch_ohlcv(ticker, period="5d")`` -- a short period is enough
    to prove the ticker resolves, keeping the validation call cheap. Flags
    invalid only when the fetch succeeds but returns an empty DataFrame
    (Pitfall 1 -- yfinance returns an empty DataFrame, not an exception, for
    an unrecognized/delisted ticker); a stale-but-non-empty cached row for a
    previously-valid ticker also counts as valid regardless of
    live/stale status.

    On any exception (a genuine live-fetch failure with no cached row at
    all, Pitfall 4), fails open and returns ``True`` -- a transient
    network/API failure is not evidence the ticker symbol itself is
    invalid, and blocking a user's save on infrastructure flakiness would
    be worse UX than D-08 intends.
    """
    try:
        df, _status = fetch_ohlcv(ticker, period="5d")
    except Exception:
        return True
    return not df.empty
