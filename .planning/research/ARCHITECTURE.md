# Architecture Research

**Domain:** Multi-user quant recommendation + price-prediction platform (Streamlit, free-tier services)
**Researched:** 2026-07-14
**Confidence:** MEDIUM (web-search-verified against official Streamlit docs; general quant/recsys architecture patterns are well-established but not project-specific; no primary source found describing this exact combination of Streamlit + LangGraph + Supabase + yfinance at scale)

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          UI / SESSION LAYER (Streamlit)                    │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐             │
│  │ Auth/Login │ │  Profile   │ │Recommend-  │ │  Asset      │             │
│  │ (Supabase) │ │  Builder   │ │ations Page │ │  Drilldown  │             │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ │ + Agent Chat│             │
│        │              │              │        └─────┬───────┘             │
├────────┴──────────────┴──────────────┴──────────────┴─────────────────────┤
│                          AGENT LAYER (LangGraph + Gemini)                  │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │  Rerank/annotate node → Explanation node → Q&A/follow-up node     │    │
│  │  (reads recommendation + prediction outputs; never recomputes     │    │
│  │   scores itself — deterministic engine stays source of truth)     │    │
│  └──────────────────────────────────────────────────────────────────┘    │
├──────────────────────────────────────────────────────────────────────────┤
│                    RECOMMENDATION ENGINE (deterministic)                   │
│  ┌────────────────┐   ┌─────────────────────┐   ┌──────────────────┐     │
│  │ Factor scoring  │ + │ Collaborative-style  │ = │ Weighted hybrid   │     │
│  │ (fundamentals,  │   │ similarity (profile   │   │ ranked shortlist  │     │
│  │  risk, momentum)│   │  ↔ asset archetypes)  │   │                    │     │
│  └────────────────┘   └─────────────────────┘   └──────────────────┘     │
├──────────────────────────────────────────────────────────────────────────┤
│                          MODEL LAYER (prediction)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────────────┐       │
│  │   SMA    │  │ XGBoost  │  │ Prophet  │  │ FinBERT sentiment    │       │
│  │ baseline │  │          │  │          │  │ (optional feature)   │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┬───────────┘       │
│       │             │             │                   │                   │
│       └─────────────┴──────┬──────┴───────────────────┘                   │
│                       Backtest harness (walk-forward, RMSE/dir-acc/Sharpe) │
├──────────────────────────────────────────────────────────────────────────┤
│                        FEATURE ENGINEERING LAYER                          │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │ Technical indicators (returns, volatility, RSI, MAs) computed      │    │
│  │ point-in-time only (no lookahead) → shared feature frame used by   │    │
│  │ both training/backtest and live prediction (single source of truth)│    │
│  └──────────────────────────────────────────────────────────────────┘    │
├──────────────────────────────────────────────────────────────────────────┤
│                    DATA LAYER + CACHE (foundation)                        │
│  ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌────────────────────┐    │
│  │ yfinance │  │ NewsAPI/  │  │  Supabase  │  │ st.cache_data /     │    │
│  │ (prices) │  │ AlphaVant.│  │ (profiles, │  │ st.cache_resource   │    │
│  │          │  │ (news)    │  │ history)   │  │ + TTL, keyed by     │    │
│  │          │  │           │  │            │  │ ticker/date-range   │    │
│  └──────────┘  └───────────┘  └────────────┘  └────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

The stack is a **layered pipeline, not a services architecture**: each layer is a Python module boundary within one Streamlit process, not a separate deployable service. This matches the free-tier, single-Streamlit-Community-Cloud-instance constraint — there is no budget or need for microservices, queues, or separate compute here.

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|-------------------------|
| Data layer | Fetch + cache raw prices (yfinance), news (NewsAPI/Alpha Vantage), and persisted user data (Supabase); own all rate-limit handling and staleness policy | Thin wrapper functions decorated with `st.cache_data(ttl=...)`; optional disk-persisted cache (SQLite/parquet) for cross-session reuse beyond Streamlit's in-memory cache lifetime |
| Feature engineering | Turn raw OHLCV + news into point-in-time technical indicators and sentiment scores; single computation path shared by backtesting and live inference | Pure functions operating on pandas DataFrames, no I/O; strict "only past data" discipline enforced here, not just at model-eval time |
| Model layer | Produce price predictions + confidence intervals per model (SMA, XGBoost, Prophet) and run walk-forward backtests (RMSE, directional accuracy, Sharpe) | One class/module per model implementing a common interface (`fit`, `predict`, `backtest`); models never call the data layer directly — they receive feature frames |
| Recommendation engine | Deterministic hybrid scoring (factor scoring + collaborative-style profile↔asset similarity) producing a ranked, explainable shortlist | Weighted-sum scorer: `final_score = w1*factor_score + w2*similarity_score`; pure function of (user profile, asset feature set) → ranked list; fully unit-testable without network/LLM calls |
| Agent layer | Rerank/annotate the deterministic shortlist with plain-English reasoning, answer follow-up Q&A; never the primary scorer | LangGraph `StateGraph` with typed state (recommendation output + prediction output as read-only inputs); Gemini free-tier as the LLM; agent responses cached per (profile-hash + shortlist-hash) to conserve Gemini free-tier quota |
| UI / session state | Render pages, own per-user `st.session_state`, orchestrate calls into the layers below, handle auth-gated navigation | Streamlit `st.Page` + `st.navigation` multipage app; session_state holds auth token, profile, and cached-in-memory results for the current rerun cycle |
| Auth / persistence | User signup/login, profile + recommendation-history persistence across sessions | Supabase Auth (JWT) + Supabase Postgres tables, accessed via `supabase-py` client or `st_supabase_connection`; token stored in `st.session_state`, verified server-side per request — never rely on a global/module-level session object |

## Recommended Project Structure

```
src/
├── data/                    # Data layer — all external I/O lives here
│   ├── prices.py            # yfinance wrapper: fetch_ohlcv(ticker, range) -> DataFrame
│   ├── news.py               # NewsAPI/Alpha Vantage wrapper
│   ├── cache.py               # st.cache_data/st.cache_resource decorators, TTL config, disk cache fallback
│   └── supabase_client.py    # Supabase client init, profile/history CRUD
├── features/                 # Feature engineering — pure functions, no I/O
│   ├── technical.py          # returns, volatility, RSI, moving averages (point-in-time only)
│   ├── sentiment.py          # FinBERT scoring of news text
│   └── feature_frame.py      # assembles the single shared feature DataFrame per asset
├── models/                   # Model layer — one module per model, common interface
│   ├── base.py               # PredictorBase interface: fit/predict/backtest
│   ├── sma.py
│   ├── xgboost_model.py
│   ├── prophet_model.py
│   └── backtest.py           # walk-forward harness: RMSE, directional accuracy, Sharpe
├── recommendation/           # Deterministic hybrid recommendation engine
│   ├── factor_scoring.py     # fundamentals/risk/momentum scoring per asset
│   ├── similarity.py         # profile ↔ asset-archetype collaborative-style scoring
│   └── engine.py             # combines both into final ranked shortlist
├── agent/                     # LLM agent layer — LangGraph + Gemini
│   ├── graph.py               # StateGraph definition: rerank node, explain node, Q&A node
│   ├── prompts.py
│   └── agent_cache.py         # caches agent responses per (profile+shortlist) hash
├── auth/                      # Auth/session helpers wrapping Supabase
│   └── session.py              # per-user session_state helpers, token verification
├── pages/                      # Streamlit multipage app (st.Page targets)
│   ├── 1_profile.py
│   ├── 2_recommendations.py
│   └── 3_asset_detail.py       # prediction + backtest + agent chat
├── app.py                      # entrypoint: st.navigation router
└── config.py                    # env vars, API keys, rate-limit constants
```

### Structure Rationale

- **`data/`, `features/`, `models/`, `recommendation/`, `agent/` are decoupled from `pages/`:** every layer below the UI is plain Python with no Streamlit imports except in `data/cache.py`. This means the whole pipeline (data → features → models → recommendation → agent) can be run and tested from a script or notebook without launching the Streamlit app — critical given free-tier rate limits make iteration expensive if every test requires a full UI rerun.
- **`data/cache.py` is a single chokepoint:** all yfinance/NewsAPI/Gemini calls route through here so TTL policy, disk-persistence fallback, and backoff/retry logic live in one place instead of being duplicated per call site.
- **`recommendation/engine.py` has no Gemini/agent dependency:** the deterministic engine must be fully functional and testable with zero LLM calls, per the project's explicit constraint that the agent reranks/annotates rather than replaces scoring.
- **`agent/` only reads outputs of `recommendation/` and `models/`:** it takes the ranked shortlist and prediction objects as input state, never calls `data/` or recomputes scores — enforces the "agent on top, not instead of" boundary architecturally, not just by convention.

## Architectural Patterns

### Pattern 1: Cache-first data access layer

**What:** Every external call (yfinance, NewsAPI, Gemini) is wrapped by a caching decorator with an explicit TTL before any other code touches it. No component calls `yfinance.download()` or the NewsAPI client directly — only `data/prices.py` and `data/news.py` do, and both are `@st.cache_data(ttl=...)`-wrapped.
**When to use:** Always, for this project — free-tier rate limits on yfinance, NewsAPI, and Gemini make this non-negotiable, not an optimization.
**Trade-offs:** Adds one layer of indirection; requires choosing sensible TTLs per data type (price data can tolerate hours of staleness for a research tool, news/sentiment less so, agent explanations can be cached longer since they're keyed on already-cached inputs). Streamlit's in-memory cache resets on app restart/sleep (Community Cloud apps sleep when idle) — pair with a disk-persisted cache (SQLite or parquet files) for data that should survive a cold start.

**Example:**
```python
import streamlit as st
import yfinance as yf

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ohlcv(ticker: str, period: str = "1y") -> "pd.DataFrame":
    return yf.download(ticker, period=period, progress=False)
```

### Pattern 2: Deterministic core, agent overlay

**What:** The recommendation engine and model layer produce their full output (ranked shortlist, predictions, confidence intervals, backtest metrics) with zero dependency on the LLM. The agent layer is invoked afterward, receives that output as read-only input state, and only reranks/annotates/explains — it cannot alter the underlying scores.
**When to use:** Always, per the project's explicit "agent reranks/annotates, doesn't replace scoring" decision — this also mirrors the general industry pattern of wrapping deterministic recall+rank pipelines with an agentic orchestration layer for explainability and Q&A rather than letting the LLM be the ranker.
**Trade-offs:** Slightly more plumbing (two output objects — deterministic result and agent-annotated result — must both be modeled), but this buys testability (the core pipeline can be unit-tested without any LLM/network calls), cost control (Gemini free-tier calls are minimized to only the final annotation step, not every intermediate decision), and reproducibility (identical profile+asset inputs always produce identical rankings, only the prose explanation can vary).

**Example (conceptual):**
```python
# recommendation/engine.py — pure, deterministic
ranked = recommendation_engine.rank(profile, asset_universe)  # no LLM calls

# agent/graph.py — LangGraph node wraps the deterministic output
def annotate_node(state):
    state["explanations"] = gemini_explain(state["ranked_shortlist"], state["profile"])
    return state
```

### Pattern 3: Shared feature frame (no train/serve skew, no lookahead)

**What:** Feature engineering happens in one code path (`features/feature_frame.py`) used identically by the backtest harness and the live prediction call. Every feature computation is point-in-time — a moving average, RSI, or sentiment score for date `t` uses only data with timestamp `≤ t`.
**When to use:** Always — this is a hard project constraint ("no lookahead bias and walk-forward-style validation are non-negotiable").
**Trade-offs:** Requires more upfront discipline in feature function design (windowed/rolling operations only, no `.shift(-1)` or full-history joins), but prevents a class of bug that silently inflates backtest accuracy and only surfaces as real-world underperformance — the most expensive kind of mistake to catch late.

## Data Flow

### Request Flow (recommendation → drilldown)

```
[User logs in]
    ↓
[Supabase Auth verifies token] → [st.session_state stores user_id + profile]
    ↓
[User completes/loads investor profile] → [Supabase: profile persisted]
    ↓
[Recommendations page loads]
    ↓
[data layer: fetch cached prices/news for asset universe] (cache hit in normal case)
    ↓
[features layer: compute point-in-time feature frame per asset]
    ↓
[recommendation engine: factor score + similarity score → weighted hybrid rank] (deterministic)
    ↓
[agent layer: LangGraph node reranks/annotates top-N with plain-English thesis] (1 Gemini call, cached)
    ↓
[UI renders ranked, explained shortlist]
    ↓ (user clicks an asset)
[Asset detail page: fetch/backtest SMA + XGBoost + Prophet predictions] (model layer, cached per ticker+model)
    ↓
[UI renders forecast + confidence interval + backtest metrics]
    ↓ (user asks a follow-up question)
[agent layer: Q&A node answers using cached recommendation + prediction context] (1 Gemini call per question)
```

### Session/State Management

```
[Supabase Auth token]
    ↓ (stored per-session, never module-level/global)
[st.session_state] ←→ [page navigation via st.navigation] ←→ [per-page widget state]
    ↓
[Cross-page data: profile, last-computed shortlist, selected asset] held in st.session_state
    ↓ (persisted subset written back to Supabase on change: profile edits, saved recommendations)
```

Critical constraint surfaced in research: naive global session objects in Streamlit + Supabase integrations have been reported to leak one user's login across all visitors of a shared server process. Auth state must live in `st.session_state` (per-browser-session) and be re-verified server-side, never cached in a module-level variable or `st.cache_resource`.

### Key Data Flows

1. **Cold-start recommendation flow:** first-time load with no cache → data layer fetches from yfinance/NewsAPI (rate-limit risk highest here) → subsequent reruns/users hit cache until TTL expires. This is the flow to stress-test rate-limit handling against.
2. **Backtest/validation flow:** entirely offline, no live API calls — feature frame + historical prices → walk-forward split → per-window fit/predict → aggregate RMSE/directional-accuracy/Sharpe. This flow should be fully runnable without touching the UI or the agent layer, enabling fast iteration on model quality independent of the rest of the app.
3. **Agent explanation flow:** only triggered after the deterministic shortlist exists; keyed/cached on a hash of (profile, shortlist) so repeated views by the same user don't re-spend Gemini free-tier quota.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|---------------------------|
| 0-1k users (portfolio/demo scale) | Current design is sufficient: single Streamlit Community Cloud instance, in-memory `st.cache_data`/`st.cache_resource` plus a lightweight disk cache, Supabase free tier for auth/persistence. No queueing needed. |
| 1k-10k users | First bottlenecks: yfinance/NewsAPI free-tier rate limits shared across *all* users hitting the same process, and Gemini free-tier request quota. Mitigate by moving from per-session in-memory cache to a shared cache table in Supabase Postgres (or Redis if budget allows) keyed by ticker+date so cache hits are shared across users, not per-session; consider a scheduled background refresh (e.g., nightly) for the asset universe's price/feature data instead of on-demand fetches. |
| 10k+ users | Free-tier ceiling reached — this is out of scope for the stated $0 budget constraint; would require paid data/LLM tiers or self-hosted alternatives (e.g., swap yfinance for a paid market-data API, self-host an open-weight LLM instead of Gemini free tier). Not a near-term concern for this project. |

### Scaling Priorities

1. **First bottleneck:** Free-tier API rate limits (yfinance unofficial/undocumented limits, NewsAPI free-tier daily cap, Gemini free-tier RPM/RPD caps) shared across concurrent users on one Streamlit process. Fix: aggressive shared caching with sensible TTLs (price data can be hours-stale for a research tool; news/sentiment can be TTL'd at the day level), request batching, and exponential backoff with a visible "data temporarily unavailable" fallback in the UI rather than a hard crash.
2. **Second bottleneck:** Streamlit reruns the entire script on every interaction — without careful caching, a single UI click (e.g., changing a slider) can retrigger expensive model fit/predict calls. Fix: cache at the model/prediction layer (`st.cache_data` keyed by ticker+model+params), not just at the raw-data layer.

## Anti-Patterns

### Anti-Pattern 1: Calling external APIs directly from UI/page code

**What people do:** Import `yfinance`/`NewsAPI` client/Gemini SDK directly inside a `pages/*.py` file and call it inline with widget values.
**Why it's wrong:** Bypasses the single caching chokepoint, makes rate-limit handling inconsistent across pages, and makes the pipeline untestable without a live Streamlit session.
**Do this instead:** Every external call goes through `data/` (or `agent/agent_cache.py` for Gemini), which owns caching, TTL, retry/backoff, and fallback behavior.

### Anti-Pattern 2: Letting the LLM agent compute or override recommendation scores

**What people do:** Ask the LLM to "look at this data and rank these assets" directly, or let it adjust factor weights on the fly.
**Why it's wrong:** Breaks determinism (same inputs, different outputs across runs), makes testing/backtesting the recommendation logic impossible, burns free-tier LLM quota on work a cheap deterministic function already does well, and undermines the "explainable, reproducible" value proposition.
**Do this instead:** Deterministic engine always computes the ranking; the agent only explains/reranks within already-scored candidates (e.g., may reorder the top-N by narrative fit but does not introduce new candidates or change underlying factor scores) or answers Q&A about the existing result.

### Anti-Pattern 3: Feature computation that leaks future data

**What people do:** Compute a rolling indicator (moving average, volatility) over the full dataset before splitting into train/test, or use `.shift(-n)` style lookback that inadvertently pulls future rows.
**Why it's wrong:** Backtest metrics look artificially good, and the model fails in production because it was implicitly trained on information it wouldn't have had at decision time. This is the single most damaging and hardest-to-detect class of bug in this domain.
**Do this instead:** Compute all features inside the feature layer using only `.rolling()`/`.expanding()` windows anchored at or before the current row; validate the backtest harness itself with a unit test that intentionally injects a future-only signal and asserts it does NOT improve backtest accuracy.

### Anti-Pattern 4: Global/module-level auth state

**What people do:** Store the logged-in user or Supabase client as a module-level singleton or `st.cache_resource`-wrapped object shared across all users of the process.
**Why it's wrong:** Streamlit Community Cloud runs one process serving all users; anything not scoped to `st.session_state` is shared across every visitor's browser session — this has caused real reported incidents of one user's Supabase login leaking to other visitors.
**Do this instead:** Auth token and user identity live only in `st.session_state`; the Supabase *client* (stateless connection object) can be `st.cache_resource`-shared, but the *session/token* never can.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|----------------------|-------|
| yfinance | Wrapped in `data/prices.py`, `st.cache_data(ttl=...)`, batch multiple tickers per call where possible, jittered retry/backoff on failure | Unofficial/undocumented rate limits (Yahoo can 429 without clear published thresholds); not designed for production-critical uptime — treat all price fetches as "best effort with cached fallback," never a hard dependency for rendering a page |
| NewsAPI / Alpha Vantage | Wrapped in `data/news.py`, cached at day-level TTL, fetched only when sentiment feature is opted in (per project's "optionally include news-sentiment scoring" requirement) | Free tier has a hard daily request cap — fetch per-asset news in batches or on a schedule rather than per-user-view |
| Gemini API (via LangGraph) | Wrapped in `agent/agent_cache.py`, invoked only after deterministic recommendation is final, cached per (profile-hash + shortlist-hash) | Free tier has RPM/RPD caps; minimize call count by caching aggressively and batching the rerank+explain+Q&A into as few LLM calls as the LangGraph design allows |
| Supabase (Auth + Postgres) | `supabase-py` client (or `st_supabase_connection`), client object `st.cache_resource`-shared, session/token in `st.session_state` only | Free tier has connection/row limits — fine at 0-1k user scale; watch for the multi-session-leak pitfall found in community reports |
| Streamlit Community Cloud | Hosting only — no code changes needed beyond respecting sleep/wake behavior (in-memory cache resets on cold start) | Design disk-persisted cache fallback so a cold-started app doesn't immediately hammer rate-limited APIs to rebuild its cache |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|----------------|-------|
| `data/` ↔ `features/` | Direct function call, DataFrame in/out | `features/` never imports Streamlit or does I/O — keeps it independently testable |
| `features/` ↔ `models/` | Direct function call, feature DataFrame in, prediction object out | Common `PredictorBase` interface (`fit`/`predict`/`backtest`) so adding LSTM/ARIMA later doesn't change call sites |
| `models/` + `recommendation/` ↔ `agent/` | Agent layer receives fully-computed outputs as LangGraph state input, read-only | Enforces the deterministic-core/agent-overlay boundary architecturally |
| `agent/`, `recommendation/`, `models/` ↔ `pages/` | Called directly from page scripts, results cached via `st.cache_data` at the page-orchestration level | No REST/API layer needed at this scale — it's all one Python process |
| `auth/` ↔ `pages/` | Every page checks `st.session_state` auth status at the top before rendering | Central `require_auth()` helper rather than duplicated checks per page |

## Sources

- [Multipage apps - Streamlit Docs](https://docs.streamlit.io/develop/concepts/multipage-apps)
- [Define multipage apps with st.Page and st.navigation - Streamlit Docs](https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation)
- [Caching overview - Streamlit Docs](https://docs.streamlit.io/develop/concepts/architecture/caching)
- [st.cache_data - Streamlit Docs](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data)
- [st.cache_resource - Streamlit Docs](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource)
- [Connect Streamlit to Supabase - Streamlit Docs](https://docs.streamlit.io/develop/tutorials/databases/supabase)
- [Multiple Sessions Issue with Supabase Auth - Streamlit Community](https://discuss.streamlit.io/t/multiple-sessions-issue-with-supabase-auth/57626)
- [st_supabase_connection (GitHub)](https://github.com/SiddhantSadangi/st_supabase_connection)
- [Rate Limiting and API Best Practices for yfinance - Sling Academy](https://www.slingacademy.com/article/rate-limiting-and-api-best-practices-for-yfinance/)
- [Caching and Performance | ranaroussi/yfinance - DeepWiki](https://deepwiki.com/ranaroussi/yfinance/6.2-caching-and-rate-limiting)
- [Quant 2.0 Architecture: Rewiring the Trading Stack for the AI Era](https://altstreet.investments/blog/quant-2-architecture-modern-trading-stack-ai-mlops)
- [Real-World Recommendation Systems in Fintech: Moving Beyond Collaborative Filtering](https://dev.to/nicholaswinst14/real-world-recommendation-systems-in-fintech-moving-beyond-collaborative-filtering-479f)
- [The Architecture of Recommendation Systems: From Collaborative Filtering to Deep Learning](https://developersvoice.com/blog/architecture/architecture-of-recommendation-systems/)
- [Walk-Forward Validation - Emergent Mind](https://www.emergentmind.com/topics/walk-forward-validation)
- [Understanding Look-Ahead Bias and How to Avoid It in Trading Strategies - Marketcalls](https://www.marketcalls.in/machine-learning/understanding-look-ahead-bias-and-how-to-avoid-it-in-trading-strategies.html)
- [Building Production-Ready AI Agents with LangGraph: A Developer's Guide to Deterministic Workflows](https://ranjankumar.in/building-production-ready-ai-agents-with-langgraph-a-developers-guide-to-deterministic-workflows)
- [Rethinking Recommendation Paradigms: From Pipelines to Agentic Recommender Systems (arXiv)](https://arxiv.org/pdf/2603.26100)

---
*Architecture research for: quant recommendation & price-prediction platform (Streamlit, free-tier)*
*Researched: 2026-07-14*
