---
phase: 02
slug: investor-profile-feature-engineering-foundation
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-03
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Browser session ↔ Streamlit process (profile page) | `st.session_state` is the only per-user store; untrusted form input crosses here | Risk tolerance, time horizon, capital, sector prefs, holdings rows (ticker/quantity/cost basis) |
| Streamlit process ↔ Supabase Postgres (`profiles`/`holdings`) | JWT-bearing HTTPS calls via a per-call scoped client; RLS is the actual enforcement boundary, not app-layer filtering | Profile scalar fields, holdings rows, `user_id` ownership |
| `src/data/profile.py` ↔ `src/data/prices.py` (ticker validation) | Untrusted external network response relayed through the existing yfinance chokepoint | Ticker validity signal only, no write-back |
| Local dev machine ↔ PyPI (`pandas-ta-classic` install) | Untrusted third-party package supply chain | Installed package code, `SUS`-flagged by legitimacy audit |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-02-01 | Elevation of Privilege / Information Disclosure | `public.holdings` RLS | high | mitigate | 4-policy RLS set (view/insert/update/delete), each keyed on `(select auth.uid()) = user_id`; proven by `tests/test_holdings_rls.py` two-user cross-access proof (select/insert/delete negative controls + same-user positive control) | closed |
| T-02-02 | Denial of Service (accidental) / Elevation of Privilege | GRANT statements on `public.holdings` | medium | mitigate | Exact GRANTs: `select, insert, update, delete` to `authenticated`; `all` to `service_role`; nothing to `anon` — verified present in migration `20260721005033_extend_profiles_and_create_holdings.sql` | closed |
| T-02-03 | Tampering | `src/data/profile.py` Supabase writes | high | mitigate | All writes via `supabase-py`'s parameterizing query builder (`.update()`/`.insert()` with dict payloads) — no raw/interpolated SQL anywhere in the module | closed |
| T-02-04 | Tampering (mass assignment) | `src/data/profile.py` payload construction | high | mitigate | `upsert_profile` uses named keyword arguments only; `upsert_holdings` extracts exactly `row["ticker"]`/`row["quantity"]`/`row.get("cost_basis")` per row instead of forwarding the input dict — proven by `test_upsert_holdings_ignores_spoofed_user_id_in_row_payload` | closed |
| T-02-05 | Tampering (XSS-adjacent) | `src/pages/profile.py` CSS-injection highlight (`_highlight_holdings_editor`) | medium | mitigate | Interpolates only the static, developer-controlled string `"holdings_editor"` into `unsafe_allow_html` — never a raw ticker or other user-entered value; verified in source | closed |
| T-02-SC | Tampering (supply chain) | `pandas-ta-classic==0.6.52` install | high | mitigate | Blocking human-verify checkpoint (Plan 02-02 Task 1) confirmed the package as a genuine `pandas-ta` fork-continuation before install; approval recorded in `02-02-SUMMARY.md` | closed |

*Status: open · closed · open — below {block_on} threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-03 | 6 | 6 | 0 | /gsd-secure-phase (L1 grep-depth, register authored at plan time, short-circuit per ASVS level 1) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-03
