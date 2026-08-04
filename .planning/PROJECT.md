# MarketMind

## What This Is

MarketMind is a full-stack web app (Streamlit + Python) that helps everyday investors research assets across stocks, ETFs, crypto, gold, and forex. It combines a traditional hybrid recommendation engine (factor scoring + collaborative-filtering-style similarity) with an interactive price-prediction module, and layers an LLM agent on top that reranks/annotates recommendations with plain-English reasoning and answers follow-up questions. Built entirely on free-tier services and shared with multiple users via Supabase auth, hosted on Streamlit Community Cloud.

## Core Value

A user gets a ranked, explainable shortlist of assets matching their investor profile, and can drill into any of them to see a price forecast with confidence intervals and backtested accuracy — recommendation and prediction work together as one pipeline, not two disconnected tools.

## Requirements

### Validated

- [x] Multiple users can sign up and log in (Supabase auth — email/password + magic link), with auth/session state strictly scoped per user — Validated in Phase 1: AUTH-01/AUTH-03 proven via 30 automated tests against a real local Supabase stack, including a real cross-user `cache_resource` session-leak vector (found and fixed during Phase 1, not merely assumed absent). Persisted profile/watchlist/history *data* (the rest of AUTH-02) remains scoped to Phase 2 (profile) and Phase 6 (watchlist/history) — Phase 1 validated the underlying persistence infrastructure (RLS-backed `profiles` table, cross-session read/write) those phases will build on.
- [x] User can build an investor profile (risk tolerance, time horizon, sector preferences, capital, existing holdings) — Validated in Phase 2 (PROFILE-01/PROFILE-02): schema + RLS-backed `holdings` child table, mass-assignment-resistant CRUD chokepoint, and builder UI all proven by 58 automated tests plus a 4/4 human UAT pass (save/reload round-trip, no-stale-cache reload, and the two review-fix scenarios CR-01/WR-01). Feature-engineering module (point-in-time-safe technical/factor features) also shipped this phase as the data layer Phase 3's recommendation engine consumes.

### Active

- [ ] User can get a ranked list of recommended assets (stocks, ETFs, crypto, gold, forex) based on their profile, using a traditional hybrid model (factor + collaborative scoring)
- [ ] User can drill into any asset and see price predictions from multiple models (starting with SMA baseline, XGBoost, Prophet) with confidence intervals
- [ ] User can see backtested model accuracy (RMSE, directional accuracy, Sharpe) for each prediction
- [ ] User can optionally include news-sentiment scoring (FinBERT) in predictions
- [ ] An LLM agent (Gemini free tier via LangGraph) reranks/annotates the traditional recommendations with a plain-English investment thesis and answers follow-up questions
- [ ] App is deployed and reachable on Streamlit Community Cloud

### Out of Scope

- Paid API tiers or paid LLM usage (Claude, paid Alpha Vantage, etc.) — free-tier-only budget constraint
- Full 7-model suite (LSTM, ARIMA, Linear Regression) in v1 — start with SMA + XGBoost + Prophet, expand later
- Portfolio optimizer and walk-forward backtesting engine (PyPortfolioOpt, vectorbt) — deferred past v1 recommendation+prediction core loop
- LLM agent as the primary recommendation scorer — agent reranks/explains on top of the deterministic traditional hybrid model, not a replacement for it
- Real brokerage integration / trade execution — research and prediction only, no trading

## Context

- Originating spec: a detailed build document (`quant_recommendation_system_spec.md`) laid out the full technical design — module structure, model interfaces, Streamlit page layouts, and a strict module-by-module build order. That spec is the primary implementation reference; this project charter scopes and sequences it.
- The repo (`MarketMind`) previously had a placeholder README describing a movie recommendation system — this is being replaced to reflect the actual financial platform.
- Motivation is dual: a genuinely useful personal investing research tool, and a portfolio piece demonstrating ML modeling, agentic LLM workflows, and full-stack build skills.
- No lookahead bias and walk-forward-style validation are non-negotiable modeling constraints carried over from the source spec, even as the model set is trimmed for v1.
- Free data sources: yfinance (prices, including forex pairs like EURUSD=X), NewsAPI/Alpha Vantage (news), FinBERT via HuggingFace transformers (sentiment) — all free tier.

## Constraints

- **Budget**: $0 infrastructure/API cost — free tiers only (yfinance, NewsAPI/Alpha Vantage free tier, Supabase free tier, Gemini API free tier, Streamlit Community Cloud). No paid Claude/OpenAI usage.
- **Tech stack**: Streamlit frontend, Python 3.11+ backend, LangGraph + Gemini API for the agent layer (swapped from the source spec's Claude API for cost reasons).
- **Deployment**: Streamlit Community Cloud — public hosting with its resource/uptime limits (app may sleep when idle, limited compute).
- **Rate limits**: yfinance, NewsAPI, and Gemini free tiers all impose request caps — model caching (`@st.cache_resource`/`@st.cache_data`) and graceful fallbacks are required, not optional.
- **Compliance**: every prediction/recommendation view must show an educational-use disclaimer — this is not financial advice.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use Gemini free tier instead of Claude API for the LLM agent | Keeps total infrastructure cost at $0 | — Pending |
| LLM agent reranks/annotates the traditional hybrid recommendations rather than replacing the scoring engine | Keeps the core recommendation flow deterministic, testable, and cheap; agent adds explainability and Q&A on top | — Pending |
| Include Forex in the v1 asset universe alongside equity/ETF/crypto/gold | User wants the full asset range from day one; yfinance supports forex pairs natively | — Pending |
| Start with a smaller model set (SMA baseline + XGBoost + Prophet) instead of all 7 models from the source spec | Reduces v1 complexity/build time; LSTM/ARIMA/Linear Regression added once the core loop works | — Pending |
| Multi-user with Supabase auth, hosted on Streamlit Community Cloud | Project is meant to be shared, not personal-only; both pieces fit the free-tier budget constraint | Validated in Phase 1 (auth/session-isolation infrastructure) |
| Automated tests for Phase 1 run against a local Supabase CLI Docker stack, not mocks or a live cloud project | Lets AUTH-02/AUTH-03 exercise real Postgres RLS and real GoTrue auth flows at zero cost with no cloud account required; a live cloud project is only needed at actual deployment time | Proven in Phase 1 — 30 tests pass against the local stack; pattern available for any later phase needing real auth/DB test coverage |
| Owner-scoped `holdings` child table (own `user_id` FK + 4 RLS policies + GRANTs), not a `jsonb` column on `profiles` | Lets holdings rows be queried/validated/RLS-checked individually rather than as an opaque blob | Proven in Phase 2 — 2-user cross-access proof (`test_holdings_rls.py`) shows RLS blocks cross-user select/insert/delete at the Postgres engine level |
| `src/data/profile.py` CRUD functions build a fresh scoped Supabase client per call (mirroring `src/auth/session.py`'s pattern) instead of using the shared `cache_resource` client | Consistent with Phase 1's fix for the cache_resource cross-user session-leak vector — avoids reintroducing the same class of bug in the profile data layer | Validated in Phase 2 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-03 after Phase 2 completion*
