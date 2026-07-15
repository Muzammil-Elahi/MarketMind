# Stack Research

**Domain:** Free-tier quant recommendation + price-prediction platform (Streamlit, multi-asset: equities/ETFs/crypto/gold/forex, LLM reranking agent)
**Researched:** 2026-07-14
**Confidence:** MEDIUM (web-verified against official docs/PyPI where possible; free-tier rate-limit specifics change often and are flagged LOW/volatile below)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11 or 3.12 | Runtime | Streamlit 1.59.x supports 3.10–3.14; Prophet/XGBoost/transformers all have prebuilt wheels for 3.11/3.12, avoiding source-build failures on Streamlit Cloud. Avoid 3.13/3.14 for now — some ML wheels (Prophet's `cmdstanpy` dep, occasionally `transformers` extras) lag newest Python by a few months. |
| Streamlit | 1.59.x | Frontend + app framework | Latest stable (July 2026). `st.cache_data`/`st.cache_resource` are mandatory here, not optional — they're the only defense against yfinance/Gemini/NewsAPI rate limits given Streamlit reruns the whole script on every interaction. |
| yfinance | latest (~1.5.x) | Market data: equities, ETFs, crypto, forex, gold futures | Free, no API key, covers every asset class in scope via ticker convention (`AAPL`, `SPY`, `BTC-USD`, `EURUSD=X`, `GC=F`). It is the only free source that spans all five asset classes with one library. **Confidence: MEDIUM** — see Pitfalls below, this is also the single biggest reliability risk in the stack. |
| XGBoost | 3.3.0 | Gradient-boosted price prediction model | Industry-standard tabular/tree model for engineered price-feature forecasting; fast to train on Streamlit Cloud's free compute, no GPU needed. |
| Prophet (`prophet`, formerly `fbprophet`) | 1.2.1 | Time-series price prediction model with trend/seasonality decomposition + built-in confidence intervals | Actively maintained (v1.2.1 Jan 2026), designed exactly for the "forecast + confidence interval + backtest" pattern this app needs; far less tuning burden than ARIMA/LSTM for a v1. |
| scikit-learn | 1.9.0 | Train/test splitting, metrics (RMSE, directional accuracy), preprocessing | De facto standard; needed regardless of which model libraries are used for consistent walk-forward evaluation utilities. |
| transformers (Hugging Face) | latest 4.x | Runs FinBERT for news-sentiment scoring | Standard way to load `ProsusAI/finbert` via `pipeline("sentiment-analysis", model="ProsusAI/finbert")` — no training required, free, runs on CPU (slow but workable at low volume). |
| google-genai | 2.8.0 | Official unified Gemini SDK | Google **fully deprecated** `google-generativeai` (support ended Nov 30, 2025). `google-genai` is the only supported path to the Gemini API now, for both AI Studio (free tier) and Vertex AI. **Confidence: HIGH** (official GitHub deprecation notice). |
| LangGraph | 1.2.x (1.0+ LTS) | Agent orchestration for the reranking/explanation/Q&A agent | Reached 1.0 LTS in 2026 with a stable graph API — reasonable to build against now without version-churn risk. Matches the project's existing decision to use LangGraph + Gemini (swapped in for the source spec's Claude). See "What NOT to Use" for a lighter alternative if the agent stays single-step. |
| langchain-google-genai | 4.0.0+ | LangChain/LangGraph ↔ Gemini connector | v4.0.0+ was rewritten on top of the new `google-genai` SDK (not the legacy `google-ai-generativelanguage` SDK) — pin to ≥4.0.0 or you'll pull in the deprecated dependency chain transitively. |
| Supabase (`supabase-py`) | 2.31.0 | Auth + Postgres persistence (user profiles, history) | Free tier (500MB Postgres, 50K MAU, 2 projects) comfortably covers a portfolio-piece app with modest multi-user traffic; ships auth, RLS-backed Postgres, and a Python client in one product — avoids hand-rolling auth. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| plotly | latest 5.x | Interactive charts (price history, forecast bands, confidence intervals) | Preferred over `matplotlib` for Streamlit — native `st.plotly_chart` interactivity (zoom/hover) matters for a forecast-drilldown UI. |
| pandas-ta-classic | latest | Technical indicators (SMA, RSI, MACD, Bollinger Bands) as XGBoost features | Use this fork, **not** the original `pandas-ta` (see What NOT to Use) or `TA-Lib` (C-extension breaks Streamlit Cloud builds without a `packages.txt` apt hack). |
| statsmodels | latest 0.14.x | SMA baseline / simple statistical backtest utilities | Lightweight for the SMA baseline model; also the natural home if ARIMA is added post-v1. |
| python-dotenv | latest | Local env var loading for API keys (Gemini, NewsAPI, Supabase) during dev | Streamlit Cloud uses `st.secrets` (`secrets.toml`) in production — use `dotenv` locally, `st.secrets` in deployment, don't hardcode either. |
| tenacity | latest | Retry/backoff wrapper around yfinance, NewsAPI, and Gemini calls | Given documented rate-limit volatility on all three free APIs, a shared retry+backoff decorator (not ad hoc try/except) should be a core architecture piece, applied at the data-fetch layer. |
| requests-cache or `st.cache_data(ttl=...)` | latest | HTTP response caching for NewsAPI/Alpha Vantage calls | NewsAPI free tier is 100 req/day and Alpha Vantage is 25 req/day — with a multi-asset universe, caching per-ticker news for hours (not re-fetching every rerun) is required to stay under quota, not a nice-to-have. |
| newsapi-python | latest | NewsAPI.org client | Thin wrapper; free "Developer" tier is explicitly ToS-restricted to development/local use (not production) — see Pitfalls, plan a fallback source. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `requirements.txt` (not Poetry/uv lockfile) | Dependency spec for Streamlit Community Cloud | Streamlit Cloud's build step reads `requirements.txt` (and optional `packages.txt` for apt deps) directly from the repo root — using Poetry/pyproject-only without a generated `requirements.txt` complicates deploys. |
| `.streamlit/secrets.toml` | Store Gemini/Supabase/NewsAPI keys in deployment | Never commit this file; configure the same keys via the Streamlit Cloud dashboard's "Secrets" UI for the deployed app. |
| pytest | Unit tests for scoring/prediction/backtest logic | Standard; especially important for walk-forward validation logic given "no lookahead bias" is a stated hard constraint. |
| ruff | Lint/format | Fast, single-tool replacement for flake8+black+isort; low overhead for a solo/portfolio project. |

## Installation

```bash
# Core data + app
pip install streamlit==1.59.2 yfinance pandas numpy plotly

# ML / forecasting
pip install xgboost==3.3.0 prophet==1.2.1 scikit-learn==1.9.0 statsmodels

# Sentiment (FinBERT)
pip install transformers torch --index-url https://download.pytorch.org/whl/cpu

# LLM agent layer (Gemini, replacing Claude from source spec)
pip install google-genai==2.8.0 langgraph langchain-google-genai>=4.0.0

# Auth/persistence
pip install supabase==2.31.0

# Resilience + indicators
pip install tenacity pandas-ta-classic requests-cache python-dotenv newsapi-python
```

**Note on `torch`:** pin the CPU-only wheel index explicitly (as above) — the default PyPI `torch` resolves a large CUDA build that will blow past Streamlit Community Cloud's 1GB memory/build-size ceiling. FinBERT inference does not need a GPU at this scale.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| yfinance | `yahooquery`, direct Yahoo endpoints | If yfinance's rate-limiting becomes a hard blocker in practice, `yahooquery` hits similar unofficial endpoints with a different implementation — same underlying fragility, but sometimes survives when yfinance is temporarily broken by a Yahoo change. Not a fix, a fallback. |
| Prophet | NeuralProphet | If you outgrow Prophet's additive-regression model and want a PyTorch-based neural forecaster with autoregression — heavier dependency, steeper learning curve, only worth it post-v1. |
| LangGraph | Plain `google-genai` calls with manual prompt orchestration (no framework) | If the agent stays a single rerank+explain call (no multi-step tool use, no branching), a framework adds overhead without payoff. Given the requirement also includes "answers follow-up questions" (implies multi-turn/stateful conversation), LangGraph's checkpointing is justified — but if scope shrinks to one-shot annotation only, drop LangGraph and call `google-genai` directly. |
| pandas-ta-classic | TA-Lib | Only if you need a specific TA-Lib-only indicator not in pandas-ta-classic's 224-indicator set — but budget time for the apt `packages.txt` C-library dance on Streamlit Cloud, or install on a machine you control and vendor pre-computed indicator values. |
| NewsAPI (dev tier) as *one* source | Alpha Vantage NEWS_SENTIMENT endpoint | Alpha Vantage's free tier (25 req/day) is even more constrained than NewsAPI's 100 req/day, but it returns pre-computed sentiment scores — useful as a secondary/cross-check source for a handful of top-priority tickers only, not a primary feed. |
| Supabase free tier | SQLite + local file storage | Only viable if you drop multi-user support entirely; the project's core requirement is multi-user auth + persisted history, which SQLite doesn't solve on ephemeral Streamlit Cloud containers (filesystem resets on redeploy/sleep). |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| `google-generativeai` (legacy Gemini SDK) | Deprecated; all GitHub support ended Nov 30, 2025. New account/API behavior may not be reflected in the frozen package. | `google-genai` (unified SDK) |
| Claude API / Anthropic SDK | Explicitly out of scope per project budget constraint ($0 infra) — paid usage, no meaningful free tier for sustained agent calls. | Gemini API free tier via `google-genai` |
| `pandas-ta` (original, unmaintained fork) | Funding/maintenance has collapsed; project itself flags sustainability risk and moved to a slower yearly-release cadence. | `pandas-ta-classic` (actively maintained community fork, 224 indicators) |
| `TA-Lib` on Streamlit Community Cloud | C-extension requiring compiled binary deps; routinely fails Streamlit Cloud's build step unless you wire up `packages.txt` apt installs, and even then it's fragile across Cloud's Linux image updates. | `pandas-ta-classic` (pure Python/pandas, no compiled deps) |
| Gemini 2.0 Flash / Flash-Lite | Deprecated and shut down June 1, 2026 — will hard-fail if referenced by model name. | Gemini 2.5 Flash-Lite (legacy but live) or the current Gemini 3.x Flash/Flash-Lite family — verify exact free-tier model list in AI Studio at build time, this list moves fast. |
| NewsAPI.org free "Developer" tier treated as a production data source | Its own ToS restricts the free tier to development/local use, not deployed apps — technically out of compliance if the deployed Streamlit Cloud app calls it live in production. | Cache aggressively and treat it as a dev-time/backfill source; for the deployed app, prefer Alpha Vantage's news endpoint (also free, ToS-cleaner for small-scale use) or pre-fetch/cache sentiment on a schedule rather than live per-request. |
| Bare `try/except` around yfinance/NewsAPI/Gemini calls with no backoff | Given all three free APIs have documented, tightening/undocumented rate limits, naive retries will burn quota faster and can worsen IP-level blocking (yfinance specifically). | `tenacity`-based exponential backoff + `st.cache_data(ttl=...)` at every external-call boundary |
| Full CUDA `torch` install | Blows the 1GB Streamlit Community Cloud memory ceiling and slows builds; unnecessary for FinBERT inference at this scale. | CPU-only `torch` wheel (see Installation) |

## Stack Patterns by Variant

**If the LLM agent stays single-turn (rerank + one-shot explanation, no follow-up Q&A):**
- Drop LangGraph, call `google-genai` directly with a structured prompt
- Because a graph/orchestration framework adds real complexity (state, checkpointing, node wiring) that only pays off once you need multi-turn state or tool-calling branches

**If the LLM agent needs multi-turn follow-up Q&A (as scoped in PROJECT.md):**
- Use LangGraph with a simple linear/ReAct graph (rerank node → explain node → chat node with conversation memory)
- Because LangGraph's built-in state/checkpointing is exactly the "answers follow-up questions" requirement, and it keeps the agent logic testable/composable as it grows

**If yfinance rate-limiting becomes a practical blocker during development:**
- Add a local on-disk/SQLite price cache with a daily refresh job, so the live app reads from cache rather than calling yfinance on every user session
- Because yfinance's undocumented rate limits are the single largest reliability risk in this stack, and Streamlit's rerun-per-interaction model multiplies call volume unless mitigated at the data layer, not just the UI layer

**If NewsAPI's dev-only ToS restriction is a concern for the "deployed, publicly reachable" requirement:**
- Switch sentiment's live news source to Alpha Vantage's NEWS_SENTIMENT endpoint (still free, 25 req/day) for the deployed app, and reserve NewsAPI for local backtesting/model development only
- Because NewsAPI's free tier terms explicitly disallow production use, which conflicts with "app is deployed and reachable on Streamlit Community Cloud"

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| `google-genai>=1.x` | `langchain-google-genai>=4.0.0` | Pin `langchain-google-genai` to ≥4.0.0 specifically — earlier 3.x releases depend on the deprecated `google-ai-generativelanguage` SDK, not `google-genai`. |
| `prophet==1.2.1` | Python 3.11/3.12, `cmdstanpy` (auto-installed dep) | Prophet's Stan backend (`cmdstanpy`) needs a compiled CmdStan binary fetched on first import — this can be slow/flaky on Streamlit Cloud's ephemeral build; consider pre-warming via a build-time script or documenting the first-load delay. |
| `transformers` + `torch` (CPU) | Python 3.11/3.12 | Use the CPU wheel index shown in Installation; avoid `torch>=2.x` GPU builds entirely on Streamlit Cloud. |
| `streamlit==1.59.x` | Python 3.10–3.14 | No known conflicts; 3.11/3.12 recommended for best ML-library wheel availability (see Core Technologies). |
| `xgboost==3.3.0` | `scikit-learn==1.9.0` | Both current as of July 2026; XGBoost's sklearn-compatible API (`XGBRegressor`) works directly with sklearn's `train_test_split`/metrics. |

## Sources

- https://ai.google.dev/gemini-api/docs/pricing — official Gemini free-tier model list (HIGH confidence, official docs, fetched directly)
- https://ai.google.dev/gemini-api/docs/rate-limits — confirms rate limits are account-tier-specific, not published as fixed numbers (HIGH confidence, official docs)
- https://github.com/google-gemini/deprecated-generative-ai-python — official deprecation notice for `google-generativeai`, support ended Nov 30 2025 (HIGH confidence)
- https://pypi.org/project/google-genai/ — current version 2.8.0 (MEDIUM confidence, web-aggregated)
- https://github.com/ranaroussi/yfinance (issues #2128, #2422, #2480) + Medium/community writeups — yfinance rate-limit/reliability pattern through 2025-2026 (MEDIUM confidence, community reports not official)
- https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app + https://docs.streamlit.io/knowledge-base/deploy/resource-limits — 1GB memory, 12h sleep, 3-app free cap (MEDIUM confidence, official docs but numbers periodically change)
- https://github.com/supabase/supabase-py + Supabase free-tier summary blogs — supabase-py 2.31.0, free tier limits (MEDIUM confidence)
- https://facebook.github.io/prophet/ + PyPI — Prophet 1.2.1 actively maintained (MEDIUM confidence)
- https://xgboost.readthedocs.io/ — XGBoost 3.3.0 (MEDIUM confidence)
- https://huggingface.co/ProsusAI/finbert — standard FinBERT checkpoint (MEDIUM confidence)
- https://newsapi.org/pricing — NewsAPI free "Developer" tier: 100 req/day, dev-only ToS (MEDIUM confidence)
- https://www.alphavantage.co/support/ + Macroption rate-limit summary — Alpha Vantage free tier: 25 req/day, 5 req/min (MEDIUM confidence)
- https://docs.streamlit.io/develop/api-reference/caching-and-state — `st.cache_data` vs `st.cache_resource` semantics (HIGH confidence, official docs)
- Community reports on `pandas-ta` maintenance risk and TA-Lib Streamlit Cloud build failures (LOW-MEDIUM confidence, forum/community sourced — verify TA-Lib avoidance decision holds if project requirements change)

---
*Stack research for: free-tier quant recommendation + price-prediction Streamlit platform*
*Researched: 2026-07-14*
