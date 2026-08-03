# Project Research Summary

**Project:** MarketMind
**Domain:** Free-tier quant recommendation + price-prediction platform (Streamlit, multi-asset: equities/ETFs/crypto/gold/forex, LLM reranking agent)
**Researched:** 2026-07-14
**Confidence:** MEDIUM

## Executive Summary

MarketMind is a multi-user, multi-asset (stocks/ETFs/crypto/gold/forex) research and price-prediction tool that experts in this space build as a **layered, single-process pipeline**: a deterministic data -> feature -> model -> recommendation pipeline, with an LLM agent bolted on top strictly to explain and rerank -- never to score. The industry pattern across competitors (Zacks, TipRanks, Simply Wall St, Tickeron) splits into "research/scoring tools" and "prediction tools"; MarketMind's differentiator is unifying both into one profile-driven flow with multi-model forecasts (SMA, XGBoost, Prophet), transparent per-model backtested accuracy, and a Gemini/LangGraph agent that explains the deterministic score in plain English and answers follow-ups -- addressing the #1 documented fintech-AI trust failure (black-box reasoning).

The recommended approach: build on Streamlit 1.59.x + Python 3.11/3.12, yfinance for all asset classes, XGBoost/Prophet/statsmodels for forecasting, FinBERT (opt-in) for sentiment, google-genai + LangGraph for the agent layer, and Supabase for auth/persistence -- all chosen because they have real, if constrained, free tiers. Architecturally, everything lives in one Streamlit process organized into strict module boundaries (data/, features/, models/, recommendation/, agent/, pages/), with a single cache-first chokepoint for every external call and a hard rule that the recommendation engine is fully deterministic and testable without any LLM dependency.

The dominant risks are all free-tier-shaped: yfinance's undocumented rate limits, NewsAPI's dev-only ToS (breaks in production), Gemini's tight multi-dimensional quotas under multi-user load, and Streamlit Community Cloud's 1GB memory ceiling colliding with FinBERT + XGBoost + Prophet running together. On top of infra risk sit two domain-specific correctness risks -- lookahead bias in feature/label construction and single-split (rather than walk-forward) backtesting -- which silently inflate reported accuracy and are expensive to retrofit. Finally, because personalized asset recommendations can be legally construed as investment advice, disclaimer/non-directive framing must be baked into every recommendation and prediction view from the first phase that renders one, not bolted on later. Mitigation for all of these is well-documented and should be built as shared infrastructure (caching/backoff wrapper, walk-forward harness, deterministic-core/agent-overlay boundary, compliance copy standard) early, rather than patched in per-feature later.

## Key Findings

### Recommended Stack

The stack centers on Streamlit 1.59.x on Python 3.11/3.12 for the app/UI, with st.cache_data/st.cache_resource treated as mandatory infrastructure (not an optimization) given Streamlit's rerun-per-interaction model combined with free-tier API rate limits. yfinance is the only free library spanning all five target asset classes, but is also the single biggest reliability risk. Forecasting uses XGBoost + Prophet + statsmodels (SMA baseline) with scikit-learn for evaluation utilities. FinBERT (via transformers, CPU-only torch) provides optional sentiment scoring. google-genai (the only supported Gemini SDK post-Nov-2025 deprecation of google-generativeai) + LangGraph 1.x powers the agent layer, justified specifically because the product requires multi-turn follow-up Q&A. Supabase covers auth + Postgres persistence on its free tier.

**Core technologies:**
- Streamlit 1.59.x -- frontend/app framework; st.cache_data/st.cache_resource are the primary defense against rate limits
- yfinance (~1.5.x) -- only free, no-key source spanning stocks/ETFs/crypto/gold/forex; MEDIUM confidence due to reliability risk
- XGBoost 3.3.0 + Prophet 1.2.1 + statsmodels -- the three prediction models (tree-based, trend/seasonality, SMA baseline)
- google-genai 2.8.0 + LangGraph 1.x + langchain-google-genai >=4.0.0 -- LLM reranking/explanation/Q&A agent (Gemini, since Claude is out of the $0 budget)
- Supabase (supabase-py 2.31.0) -- auth + Postgres persistence, free tier covers portfolio-scale traffic
- transformers + CPU-only torch -- FinBERT sentiment scoring, opt-in and lazy-loaded
- tenacity + pandas-ta-classic + plotly -- supporting: retry/backoff, technical indicators (not the unmaintained pandas-ta or build-fragile TA-Lib), interactive charts

### Expected Features

Competitor research across research-tools (Zacks/TipRanks/Simply Wall St/Morningstar), robo-advisors (Wealthfront/Betterment), and prediction tools (Tickeron/TrendSpider/AltIndex) shows the category splits cleanly, and MarketMind's value proposition is unifying them. Every table-stakes feature maps to an existing PROJECT.md requirement, so the risk isn't scope discovery but sequencing and depth (e.g., score transparency must be real factor breakdown, not decoration).

**Must have (table stakes):**
- Investor profile / risk questionnaire feeding visible personalization
- Ranked, sortable/filterable asset list with per-asset score + short "why"
- Per-asset drill-in page with price chart, prediction, and score breakdown
- Watchlist / saved assets (Supabase-backed)
- Compliance disclaimer on every recommendation/prediction view (FINRA 2214/2111.03)
- Multi-user auth + persisted history; cross-asset-class ticker search

**Should have (competitive differentiators):**
- Unified recommendation + prediction pipeline as one coherent user journey (the core bet)
- Multi-model forecasting with visible confidence intervals and per-model backtested accuracy
- LLM rerank + plain-English investment thesis + follow-up Q&A, grounded in the deterministic score
- Cross-asset-class (stocks+ETFs+crypto+gold+forex) unified profile-driven experience

**Defer (v2+):**
- Sentiment layer (FinBERT) and LLM follow-up Q&A conversational state -- add after core loop validated
- Expanded model set (LSTM/ARIMA/Linear Regression)
- Portfolio-level optimizer, cross-user aggregate signals, brokerage deep-link -- explicitly out of v1, and real trade execution / specific buy-sell price targets are anti-features that conflict with the educational-tool compliance framing

### Architecture Approach

The system is a **layered pipeline within a single Streamlit process** (not microservices) -- UI/session layer -> agent layer (LangGraph+Gemini) -> deterministic recommendation engine -> model layer (SMA/XGBoost/Prophet + backtest harness) -> feature engineering layer -> data layer/cache. Two architectural rules are load-bearing: (1) every external call (yfinance/NewsAPI/Gemini) routes through one caching chokepoint (data/cache.py) with TTL + backoff, and (2) the LLM agent is strictly an overlay -- it reads the deterministic engine's already-computed output as read-only state and never recomputes or overrides scores, preserving testability, reproducibility, and quota control.

**Major components:**
1. Data layer (data/) -- all external I/O, cache-first, owns rate-limit/backoff/staleness policy
2. Feature engineering (features/) -- pure, point-in-time-only functions shared by backtest and live inference (no lookahead)
3. Model layer (models/) -- common fit/predict/backtest interface per model, plus the walk-forward harness
4. Recommendation engine (recommendation/) -- deterministic factor + collaborative-style hybrid scorer, zero LLM dependency
5. Agent layer (agent/) -- LangGraph StateGraph (rerank -> explain -> Q&A nodes) reading recommendation/model outputs read-only
6. Auth/session (auth/) -- Supabase Auth token strictly in st.session_state, never module-level/global

### Critical Pitfalls

1. **Lookahead bias in feature/label construction** -- enforce point-in-time-only features (.shift(1) after rolling calcs, fit scalers on train fold only), add an automated leakage smoke test; must be foundational in the feature pipeline, not retrofitted.
2. **Single train/test split instead of walk-forward validation** -- implement expanding/rolling-window walk-forward backtesting for every model and report fold mean+/-std, not one point estimate; build this before shipping the accuracy-display UI.
3. **yfinance treated as stable/unlimited** -- bulk yf.download(), aggressive st.cache_data(ttl=...), exponential backoff+jitter, graceful degraded UI; build once as a shared wrapper in the earliest data-ingestion phase.
4. **Gemini free-tier quota exhaustion under multi-user load** -- cheapest capable model by default, cache LLM outputs by (profile+shortlist) hash, minimize LangGraph tool-call round-trips, track usage server-side, degrade gracefully instead of surfacing 429s.
5. **Unlicensed investment advice framing** -- non-directive UI/LLM copy ("scores highly against your profile" not "you should buy"), disclaimer on every prediction/recommendation view from the first phase that renders one, reviewed again whenever a new user-facing view is added.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation -- Data Layer, Caching, and Auth Skeleton
**Rationale:** Every other layer depends on the cache-first data chokepoint and auth/session pattern; getting these wrong is the hardest/most expensive class of bug to retrofit (cross-user leakage, rate-limit cascades).
**Delivers:** data/prices.py (yfinance, cached/backoff-wrapped), data/supabase_client.py, Supabase Auth wired into st.session_state (never global/cache_resource), base multipage app shell (st.Page/st.navigation).
**Addresses:** Multi-user auth + persisted history (table stakes)
**Avoids:** Pitfall 3 (yfinance rate-limit treated as unlimited), Pitfall 7 (cache_resource cross-user leakage), Pitfall 4/security (RLS misconfiguration)

### Phase 2: Investor Profile + Feature Engineering Foundation
**Rationale:** The recommendation engine and model layer both need a profile input and a leakage-safe feature pipeline before any scoring/prediction logic can be built or tested meaningfully.
**Delivers:** Profile builder UI + Supabase persistence; features/technical.py/feature_frame.py with point-in-time-only computation and an automated leakage smoke test.
**Uses:** pandas-ta-classic, statsmodels
**Implements:** Feature engineering layer (shared feature frame pattern)
**Avoids:** Pitfall 1 (lookahead bias) -- this is the phase where it must be caught, since retrofitting later is expensive

### Phase 3: Deterministic Recommendation Engine
**Rationale:** Must exist and be fully testable (zero LLM/network dependency) before the agent layer is built on top of it -- establishes the "deterministic core, agent overlay" boundary architecturally.
**Delivers:** Factor scoring + collaborative-style similarity -> weighted hybrid ranked shortlist; ranked asset list UI with visible score breakdown.
**Addresses:** Ranked asset list, score/rating transparency (table stakes)
**Implements:** recommendation/ module, no Gemini dependency

### Phase 4: Multi-Model Prediction + Walk-Forward Backtesting
**Rationale:** Depends on Phase 2's feature pipeline; the backtest harness (walk-forward, no lookahead) is shared infrastructure needed before any accuracy metric is shown to users -- must not ship the metrics UI before the harness exists underneath it.
**Delivers:** SMA/XGBoost/Prophet models behind a common PredictorBase interface, walk-forward backtest harness (RMSE/directional accuracy/Sharpe, fold mean+/-std), per-asset drill-in page with chart + confidence intervals.
**Addresses:** Per-asset drill-in, multi-model prediction, backtested accuracy display (P1 features)
**Avoids:** Pitfall 2 (single-split validation), Pitfall 6 (memory ceiling -- validate model footprint here first)

### Phase 5: LLM Agent Layer (Rerank + Explain)
**Rationale:** Only buildable once Phases 3 and 4 produce stable, well-defined output objects for the agent to read as input state; this ordering enforces the "agent reads, never computes" architectural rule by construction.
**Delivers:** LangGraph StateGraph (rerank/annotate node -> explanation node), Gemini integration via google-genai, response caching keyed on (profile-hash + shortlist-hash), quota tracking + graceful degradation.
**Addresses:** LLM rerank + plain-English thesis (core differentiator)
**Avoids:** Pitfall 5 (Gemini quota exhaustion), Pitfall 9 (hallucination -- context-grounding built in from the start)

### Phase 6: Compliance, Watchlist, and Polish
**Rationale:** Compliance framing should be established early (see cross-cutting note below) but this phase is where it's audited across all views once they all exist, alongside the remaining low-complexity table-stakes feature (watchlist).
**Delivers:** Disclaimer present and content-reviewed on every prediction/recommendation view; non-directive copy audit including LLM prompt language; watchlist (save from list/drill-in).
**Addresses:** Compliance disclaimer, watchlist (table stakes)
**Avoids:** Pitfall 8 (unlicensed advice framing)

### Phase 7 (v1.x, post-validation): Sentiment Layer + Conversational Q&A
**Rationale:** Explicitly deferred per FEATURES.md MVP definition -- trigger is core loop validated and users asking for it; also the phase most exposed to the 1GB memory ceiling (FinBERT) and NewsAPI's dev-only ToS, so it should be isolated from the v1 critical path.
**Delivers:** FinBERT sentiment as opt-in feature input; LangGraph conversational Q&A node with memory.
**Avoids:** Pitfall 4 (NewsAPI production ToS), Pitfall 6 (memory ceiling -- re-verify here specifically)

### Phase Ordering Rationale

- Data/auth foundation must come first because every other layer (features, models, recommendation, agent) depends on the cache chokepoint and session pattern, and both have documented severe failure modes (rate-limit cascades, cross-user leakage) that are cheap to prevent architecturally but expensive to retrofit.
- Feature engineering (with leakage testing) is deliberately isolated as its own phase before any model training, per PITFALLS.md's explicit guidance that lookahead-bias fixes are the most expensive to retrofit of any pitfall in this domain.
- The deterministic recommendation engine and the model/backtest layer are sequenced before the agent layer specifically to enforce the "deterministic core, agent overlay" architecture pattern -- the agent literally cannot be correctly built until it has stable outputs to read.
- Compliance/disclaimer framing is called out as a phase but is explicitly also a cross-cutting concern: PITFALLS.md and FEATURES.md both stress it must be present from the first phase that renders any prediction/recommendation, not deferred to a single "compliance phase" -- the roadmap should treat Phase 6 as an audit/consolidation pass, with the actual disclaimer component introduced as shared UI as early as Phase 3.
- Sentiment and conversational Q&A are pushed to v1.x/Phase 7 per FEATURES.md's explicit MVP scoping and because they carry the two most environment-specific risks (Streamlit Cloud memory ceiling, NewsAPI production ToS) that benefit from being isolated rather than blocking the core loop.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Recommendation Engine):** No single authoritative pattern found for hybrid factor+collaborative scoring in a multi-asset-class context (stocks/crypto/gold/forex behave very differently) -- needs research on how to normalize factor weights across asset classes.
- **Phase 5 (LLM Agent Layer):** LangGraph 1.0 LTS is new (2026); state/checkpointing patterns for a rerank->explain->Q&A graph combined with aggressive Gemini quota-aware caching is a less-established combination -- verify exact free-tier model list and current rate limits at build time, this moves fast.
- **Phase 7 (Sentiment + Q&A):** FinBERT memory footprint in combination with the already-loaded XGBoost/Prophet models needs empirical profiling under Streamlit Community Cloud's 1GB ceiling -- not just documentation research.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Data/Auth Foundation):** Streamlit caching (st.cache_data/st.cache_resource) and Supabase Auth integration are both officially documented (HIGH confidence sources) with well-established patterns.
- **Phase 4 (Prediction + Backtesting):** Walk-forward validation and XGBoost/Prophet usage are standard, well-documented quant patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Core version/API facts (Gemini SDK deprecation, Streamlit caching semantics) are HIGH/official; free-tier rate-limit specifics are volatile and community-sourced |
| Features | MEDIUM | Cross-checked across many competitor products and FINRA primary sources for compliance; no primary-source ToS review of every competitor |
| Architecture | MEDIUM | Streamlit-specific patterns (caching, multipage, session_state) are HIGH/official docs; the exact combination of Streamlit+LangGraph+Supabase+yfinance at scale has no single primary source, so composition is inferred from established sub-patterns |
| Pitfalls | MEDIUM | Cross-corroborated across multiple independent community sources per topic; no official curated API was available, so quota/pricing numbers are directionally correct only |

**Overall confidence:** MEDIUM

### Gaps to Address

- **Exact current free-tier rate limits (Gemini RPM/RPD, Alpha Vantage req/day, yfinance undocumented thresholds):** these move frequently -- re-verify against live provider docs at the start of Phase 1 and Phase 5, don't hardcode research-time numbers into rate-limit logic.
- **NewsAPI vs. Alpha Vantage final choice for the deployed sentiment source:** STACK.md and PITFALLS.md both flag NewsAPI's free tier as dev-only ToS-restricted; this needs to be explicitly resolved and validated against the real deployed Streamlit Cloud URL in Phase 7, not assumed to work because it worked locally.
- **Cross-asset-class factor-weight normalization:** no research source addressed how to make one hybrid scoring model behave sensibly across stocks, 24/7 crypto, and forex/gold -- flagged as a Phase 3 research item.
- **Prophet/cmdstanpy cold-start behavior on Streamlit Cloud:** STACK.md notes the Stan backend can be slow/flaky on first import in an ephemeral build environment -- needs empirical validation in Phase 4, not just documentation research.

## Sources

### Primary (HIGH confidence)
- https://ai.google.dev/gemini-api/docs/pricing, /rate-limits -- official Gemini free-tier and rate-limit docs
- https://github.com/google-gemini/deprecated-generative-ai-python -- official google-generativeai deprecation notice
- https://docs.streamlit.io/develop/api-reference/caching-and-state -- st.cache_data/st.cache_resource semantics
- https://docs.streamlit.io/develop/concepts/multipage-apps -- multipage app patterns
- https://www.finra.org/rules-guidance/rulebooks/finra-rules/2214, /key-topics/suitability/faq, /investors/insights/automated-investment-tools -- FINRA compliance rules (educational tool framing)

### Secondary (MEDIUM confidence)
- https://github.com/ranaroussi/yfinance issues #2125/#2128/#2422/#2480 + community writeups -- yfinance rate-limit/reliability behavior
- https://discuss.streamlit.io/t/multiple-sessions-issue-with-supabase-auth/57626, streamlit/streamlit#5581 -- multi-user session_state/auth leakage reports
- https://newsapi.org/pricing -- NewsAPI free "Developer" tier dev-only ToS restriction
- Competitor comparisons (WallStreetZen, Wall Street Survivor, Simply Wall St, NerdWallet, stockanalysis.com) -- feature landscape across Seeking Alpha/TipRanks/Zacks/Wealthfront/Betterment/Tickeron
- https://huggingface.co/ProsusAI/finbert + memory-requirements discussion -- FinBERT footprint on constrained environments

### Tertiary (LOW confidence)
- Single-case-study fintech UX writeups (e.g. FinAI Medium case study) -- directional only, not a competitor product
- Community forum posts on pandas-ta maintenance risk and TA-Lib build failures -- verify decision holds if requirements change

---
*Research completed: 2026-07-14*
*Ready for roadmap: yes*
