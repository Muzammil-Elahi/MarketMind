# Pitfalls Research

**Domain:** Quant recommendation & price-prediction platform (stocks/ETFs/crypto/gold/forex) — free-tier, multi-user, Streamlit Community Cloud
**Researched:** 2026-07-14
**Confidence:** MEDIUM (web-sourced, cross-corroborated across multiple independent results per topic; no official curated docs API was available in this environment, so nothing here is HIGH-tier — treat quota/pricing numbers as directionally correct and re-verify against live provider docs before locking limits into code)

## Critical Pitfalls

### Pitfall 1: Lookahead bias in feature/label construction

**What goes wrong:**
Features or training labels are built using information that would not have been available at the moment a prediction is made. Classic culprits: rolling/technical indicators (SMA, RSI, Bollinger) computed over a window that includes the "current" bar before it has closed; sentiment/news features joined on publish date rather than the date the info was actually available to a trader; labels defined as "future return over next N days" that leak into a feature column by an off-by-one shift error; scaling/normalizing (e.g. MinMaxScaler, z-score) fit on the *entire* dataset (including test data) before splitting.

**Why it happens:**
Pandas makes it trivially easy to `.rolling()`, `.shift(-1)`, or `df.merge()` across the whole DataFrame without thinking about point-in-time availability. It "just works" and produces suspiciously good backtest metrics, which developers mistake for a good model.

**How to avoid:**
- Every derived feature must only use data with a timestamp ≤ prediction time; enforce with explicit `.shift(1)` after any rolling calc, and unit-test that shifting.
- Fit scalers/encoders only on the training fold, then `.transform()` (never `.fit_transform()`) on validation/test.
- For news sentiment (FinBERT), join on the news item's *publish timestamp*, and only include items published before the prediction cutoff, not before market close of the prediction day.
- Add an automated "leakage smoke test": train on data through day T, predict day T+1, and verify no feature column has values that changed if you truncate the raw dataset at T+1 vs. include data through T+30.

**Warning signs:**
Backtest metrics that look too good (near-perfect directional accuracy, very high Sharpe on a single-model naive setup); performance that collapses when the model is run in true "paper trading" / live mode after looking great in backtest; features whose correlation with the target is suspiciously high (>0.9) for a next-day return target.

**Phase to address:**
Data/feature pipeline phase, before any model training phase begins. This must be a foundational constraint baked into the feature-engineering module, not bolted on later — retrofitting leakage fixes after models are "working" is expensive because every downstream metric has to be re-validated.

---

### Pitfall 2: Single train/test split instead of walk-forward validation

**What goes wrong:**
The project spec explicitly calls out backtested accuracy (RMSE, directional accuracy, Sharpe) as a user-facing feature. A common shortcut is a single chronological 80/20 split: train once, test once, report the numbers. This produces one noisy point estimate, is implicitly biased toward whatever regime the test window happened to be (e.g. a bull run), and doesn't validate that the model generalizes across changing market conditions — which is exactly the scenario this app will hit in production as it re-predicts on fresh data every day.

**Why it happens:**
Walk-forward validation is more code, more compute, and slower to implement than `train_test_split`. Free-tier compute (Streamlit Community Cloud's 1GB) and free-tier API budgets (yfinance/Gemini rate limits) create pressure to cut corners here first, since it's invisible to the end user if skipped.

**How to avoid:**
- Implement expanding-window or rolling-window walk-forward validation as the standard backtest procedure for every model (SMA, XGBoost, Prophet): train on window 1, test on window 2, roll forward, retrain, repeat — aggregate RMSE/directional accuracy/Sharpe across all folds, not just one.
- Report the *distribution* of fold metrics (mean ± std) in the UI, not a single number — this is more honest and also more interesting to show users.
- Reserve a single train/test split only for fast local dev-loop iteration, never for the accuracy numbers shown to end users.
- Watch for a "Sharpe > 3" or near-perfect directional accuracy on any fold — treat it as a bug to investigate (see Pitfall 1), not a win.

**Warning signs:**
Reported backtest accuracy that doesn't hold up when you manually re-run the model on a different historical window; single point-estimate metrics with no confidence interval or fold-to-fold variance shown; a model that looks great on gold/SPY (trending assets) but the same code path is never validated on a choppy/sideways asset.

**Phase to address:**
Model-training/backtesting phase (the phase that implements SMA/XGBoost/Prophet + backtest metrics). Should be the same phase that builds the "confidence intervals and backtested accuracy" requirement — don't ship the metrics UI before the walk-forward engine exists underneath it.

---

### Pitfall 3: yfinance treated as a stable, unlimited API

**What goes wrong:**
yfinance is not an official Yahoo Finance API — it scrapes Yahoo's web/JSON endpoints. Under concurrent or rapid requests (e.g. looping per-ticker `yf.Ticker(x).history()` calls for a multi-asset recommendation scan across stocks/ETFs/crypto/gold/forex), Yahoo's servers return HTTP 429 and can temporarily IP-ban the caller. Because Streamlit Community Cloud apps run on shared infra, this can also mean noisy-neighbor effects. Under multi-user load (several users triggering scans/predictions concurrently) this gets worse, not better.

**Why it happens:**
yfinance "just works" in local dev with a handful of manual test requests, so the rate-limit risk isn't visible until real usage patterns (many tickers × many users) start hitting it.

**How to avoid:**
- Use bulk `yf.download(tickers=[...])` instead of looping single-ticker `yf.Ticker()` calls wherever possible.
- Cache all price data aggressively with `st.cache_data(ttl=...)` (e.g. 15 min–1 day depending on use case) so repeat requests within a session/across users hit cache, not Yahoo.
- Add exponential backoff + retry with jitter around yfinance calls, and a graceful degraded UI state ("price data temporarily unavailable, showing cached data from [timestamp]") rather than a crash.
- Set a realistic User-Agent header and throttle request rate explicitly (don't rely on default yfinance behavior).
- Consider a lightweight local SQLite/Parquet cache layer that persists fetched price history between app restarts, so a cold Streamlit Cloud container doesn't re-fetch everything from Yahoo on every wake-up.

**Warning signs:**
Intermittent `YFRateLimitError` / "Too Many Requests" in logs, especially correlated with multiple users active or with the recommendation engine scanning many tickers at once; app appears to work fine solo in dev but breaks in multi-user demo/testing.

**Phase to address:**
Data ingestion/pipeline phase (earliest phase that touches yfinance) — build the caching + backoff wrapper once, as a shared utility, and have every other module (recommendation scoring, prediction, backtesting) call through it rather than hitting yfinance directly.

---

### Pitfall 4: NewsAPI free tier is not legally or technically usable in a deployed app

**What goes wrong:**
NewsAPI.org's free "Developer" plan is restricted to **localhost/development use only** — its CORS policy blocks requests from deployed domains, articles are delayed 24 hours, and the terms of service explicitly forbid production, staging, or commercial use. A Streamlit Community Cloud deployment is a public production URL. This means the sentiment/news feature, as scoped ("NewsAPI/Alpha Vantage for news"), may simply not work — or worse, silently violate ToS — once deployed, even though it worked fine when tested locally.

**Why it happens:**
The free-tier restriction is easy to miss because local development against `localhost` works perfectly; the failure only appears after deployment, which is often late in a build cycle.

**How to avoid:**
- Confirm this constraint explicitly before building the news-sentiment feature: since backend server-side requests (not a browser) call NewsAPI, CORS may not literally block it (CORS is a browser mechanism), but the ToS production-use prohibition still applies contractually.
- Prefer Alpha Vantage's free News & Sentiment endpoint (already listed as an alternative in the project's data sources) for the deployed environment, since its free tier is intended for broader (though still rate-limited, ~25 requests/day on some free tiers — verify current limits) usage without the explicit "dev-only" ToS restriction NewsAPI.org imposes.
- Whatever source is chosen, cache news/sentiment results aggressively (`st.cache_data` with multi-hour TTL) since news doesn't need per-second freshness, and this also protects against low daily request caps.
- Build a no-news-available fallback path (recommendation/prediction should degrade gracefully to price-only signals) so this dependency is never a hard blocker.

**Warning signs:**
News/sentiment feature works in local dev, breaks or gets rejected once running on the deployed Streamlit Cloud URL; NewsAPI account flagged or throttled after deployment.

**Phase to address:**
News/sentiment integration phase — resolve the provider choice (Alpha Vantage vs. NewsAPI) and validate it under the *deployed* environment, not just local dev, before wiring FinBERT scoring on top of it.

---

### Pitfall 5: Gemini free-tier limits break the multi-user agent layer under real usage

**What goes wrong:**
Gemini API free-tier quotas are tight and multi-dimensional (requests/minute, tokens/minute, requests/day — e.g. roughly 10–15 RPM and 1,500 RPD depending on model, with more capable models like 2.5 Pro capped as low as 5 RPM/50 RPD). Any single dimension being exceeded triggers a 429, even if the others are fine. With multiple users each triggering LLM reranking/annotation and follow-up Q&A, the app can burn through the daily cap quickly, or hit per-minute limits during any burst of concurrent activity (e.g. a demo with several reviewers using it at once).

**Why it happens:**
Free-tier quotas look generous in isolation (1,500/day sounds like a lot) but the agent is invoked per recommendation view *and* per follow-up question *and* potentially multiple LLM calls per LangGraph agent turn (tool calls, reasoning steps) — actual request count per user session can be 3-10x what a naive estimate assumes.

**How to avoid:**
- Choose the cheapest capable model (e.g. Flash-tier, not Pro-tier) for the agent by default, reserving any higher-capability model only for a single final "explain this" call, not every intermediate agent step.
- Cache LLM outputs keyed on (asset, profile-hash, ranking-snapshot) with `st.cache_data`, so repeated views of the same recommendation don't re-call the LLM.
- Add explicit rate-limit-aware backoff and a friendly degraded UI ("AI explanation temporarily unavailable — showing the deterministic ranking only") instead of surfacing a raw API error to the user.
- Track daily usage server-side (e.g. a Supabase counter) and proactively disable/queue the LLM feature once nearing the daily cap, rather than letting users hit failures individually.
- Design the LangGraph agent to minimize tool-call round-trips (each round-trip is a separate Gemini call against the RPM budget).

**Warning signs:**
429 errors from Gemini appearing in logs correlated with more than one active user; agent responses becoming slow/degraded during any concurrent testing; daily quota exhausted early in the day after only moderate testing traffic.

**Phase to address:**
LLM agent integration phase — build the caching + quota-tracking + graceful-degradation wrapper as part of the initial agent implementation, not as a later hardening pass, since this is the single most usage-sensitive dependency in the whole app.

---

### Pitfall 6: Streamlit Community Cloud's 1GB memory ceiling collides with FinBERT + multiple ML models in one process

**What goes wrong:**
Streamlit Community Cloud apps get a hard ~1GB memory allocation. FinBERT (ProsusAI/finbert, ~400MB+ on disk, plus PyTorch/transformers runtime overhead once loaded) loaded alongside XGBoost models, Prophet's Stan-based backend, pandas DataFrames of multi-asset price history, and the base Streamlit/Python runtime itself can push a single-user session close to or over that limit — and Streamlit Cloud is a *shared* environment across all sessions of the deployed app, not one container per user, so multiple concurrent users compound memory pressure. When the limit is hit, the app throws a resource-limit error page and may need a manual reboot.

**Why it happens:**
It's easy to prototype FinBERT + XGBoost + Prophet locally on a dev machine with 8-16GB+ RAM and never notice the footprint; the constraint only bites after deployment to the 1GB Community Cloud tier.

**How to avoid:**
- Load FinBERT (and any other heavy model) exactly once per process via `st.cache_resource`, never per-request or per-session — verify with a memory profiler that repeated calls don't reload it.
- Make FinBERT/sentiment scoring opt-in (the spec already frames it as optional) so it's not loaded into memory for users who don't request it — lazy-load on first use, not at app startup.
- Consider a distilled/smaller sentiment model as a fallback default (e.g. a DistilBERT-based finance sentiment model) if FinBERT alone proves too heavy in combination with the price-prediction models.
- Limit Prophet's internal precompiled backend and XGBoost's `n_estimators`/`max_depth` to values reasonable for a memory-constrained container; avoid loading full historical price data for every asset in the universe into memory at once — fetch/predict per-asset on demand.
- Profile actual memory usage (e.g. via `tracemalloc`/`psutil` logging, or simply watching the Streamlit Cloud resource dashboard) under realistic multi-model, multi-user load before considering the app "done," not just under a single local smoke test.

**Warning signs:**
"This app has gone over its resource limits" error page in Streamlit Cloud; app becomes sluggish or crashes specifically when FinBERT sentiment scoring is enabled alongside price prediction; memory usage climbs monotonically across a session (suggests models are being reloaded rather than cached).

**Phase to address:**
Should be validated incrementally: FinBERT/sentiment integration phase (verify FinBERT's own footprint with `st.cache_resource`), and again at the deployment/hardening phase once all models are combined in the real app — this is a compounding risk that needs re-checking as each new model is added, not a one-time check.

---

### Pitfall 7: `st.cache_resource`/`st.cache_data` misused, causing stale predictions or cross-user data leakage

**What goes wrong:**
Two distinct failure modes: (1) using `st.cache_data` (or no caching at all) for expensive model objects like a loaded FinBERT pipeline or trained XGBoost model causes them to be reloaded/retrained on every rerun, wasting the 1GB memory/CPU budget and making the app painfully slow; (2) using `st.cache_resource` for *mutable* objects (e.g. a DataFrame accumulator, a live in-memory "portfolio" object, or a per-user LangGraph agent state) causes that object to be shared by reference across all users and sessions of the deployed app — a classic multi-user bug where one user's action mutates state another user sees, since `st.session_state` is per-connection but globals and `cache_resource` objects are process-wide.

**Why it happens:**
The distinction between "data" (safe to copy, use `cache_data`) and "resource" (a singleton to share by reference, use `cache_resource`) is subtle, and Streamlit's docs/tutorials often show ML model caching examples without emphasizing the thread-safety and cross-user-sharing implications for a multi-user Community Cloud deployment (versus a single-user local app).

**How to avoid:**
- Rule of thumb: `st.cache_resource` only for read-mostly, effectively-immutable singletons (loaded model weights, a DB connection pool). Never store per-user mutable state there.
- All per-user state (investor profile, current recommendation set, chat history with the agent) belongs in `st.session_state` or persisted to Supabase — never in a bare global or `cache_resource`-wrapped mutable object.
- Set explicit TTLs on `st.cache_data` for anything time-sensitive (live prices, news sentiment) — an un-TTL'd cache silently serves stale market data indefinitely, which is especially bad for a price-prediction app where "as of" freshness matters.
- Be deliberate with underscore-prefixed arguments (which skip Streamlit's hashing) — don't hide an argument that should actually invalidate the cache (e.g. hiding the model version or ticker) behind an underscore, or users will see wrong/stale results without any code error.
- Add a lightweight integration test that simulates two concurrent "users" (two sessions) with different profiles and asserts their session-scoped data never cross-contaminates.

**Warning signs:**
One user's recommendation list or chat history appearing to another user; predictions that don't change even after the underlying price data clearly has (stale cache); app slowing down over time in a way that correlates with model-loading code paths, suggesting resources are being re-created instead of cached.

**Phase to address:**
Should be a cross-cutting concern enforced from the first phase that introduces any cached model or shared resource (likely the prediction-model phase, then re-verified in the multi-user auth/Supabase phase once real concurrent users exist).

---

### Pitfall 8: Presenting predictions/recommendations in a way that constitutes unlicensed investment advice

**What goes wrong:**
Under the Investment Advisers Act of 1940 (and analogous state regimes), providing algorithm-based, personalized portfolio or asset recommendations can be legally construed as "investment advice," which triggers SEC/state Registered Investment Adviser (RIA) obligations and fiduciary duty — obligations a hobby/portfolio project has no intention or ability to meet. A generic disclaimer alone does not guarantee legal safety if the app's actual behavior (personalized ranked recommendations tailored to a user's stated risk tolerance/capital/holdings, framed as "you should consider X") functions like individualized advice rather than general educational content.

**Why it happens:**
Teams focus on the ML/product build and treat the disclaimer as a checkbox UI element added at the end, without considering that the *product framing itself* (personalized recommendations + specific price targets + "buy/consider" language) is the actual legal risk factor, not just the absence of a disclaimer.

**How to avoid:**
- Frame all outputs as educational/informational research aids, never as personalized buy/sell recommendations — avoid imperative language ("buy," "you should," "recommended action") in favor of descriptive framing ("this asset scores highly against your stated profile criteria," "the model's historical accuracy for this asset is X").
- Show the "not financial advice" disclaimer on every prediction/recommendation view (already a stated constraint) — but also bake the disclaimer concept into copywriting throughout the UI, not just a footer.
- Never claim or imply guaranteed returns; always pair any prediction with its backtested error bars/confidence intervals and a clear statement that past performance/backtest accuracy does not guarantee future results.
- Keep the LLM agent's explanatory language reviewed/constrained (e.g. via prompt engineering and possibly output filtering) so it does not itself drift into imperative advice language ("you should buy this now") even if the underlying deterministic score is neutral — LLM hallucination/over-confidence is a distinct additional risk on top of the ranking engine itself (see Pitfall 9).
- This is a portfolio/personal project on a free-tier budget, not a registered advisory business — consult that framing explicitly in any public-facing About/Terms page: the tool is for research/education only, not individualized advice, and users should consult a licensed professional before acting.

**Warning signs:**
UI copy or LLM-generated text using directive language ("Buy," "Sell," "You should invest in..."); marketing/README language implying the tool gives "advice" rather than "research" or "analysis"; absence of a disclaimer on any page that shows a prediction or ranked list, including any newly added page added later in development that the team forgot to disclaim.

**Phase to address:**
Should be established as a UI/content standard in the earliest phase that renders any recommendation or prediction (not deferred to a "compliance phase" at the end), and re-verified at every subsequent phase that adds a new user-facing view, including the LLM agent phase where output isn't fully deterministic.

---

### Pitfall 9: LLM agent hallucinating financial facts or overstating confidence

**What goes wrong:**
The LLM agent (Gemini via LangGraph) reranks/annotates recommendations and answers free-form follow-up questions. LLMs are well-documented to hallucinate — generating plausible-sounding but false claims (e.g. inventing a company fundamental, misstating a backtested accuracy number, fabricating a news event) with the same confident tone as accurate output. In a financial context this is a specific liability and trust risk (the Air Canada chatbot case establishes that companies can be held liable for their AI's false claims), and is materially worse than a generic chatbot hallucination because users may act on financial "facts" it states.

**Why it happens:**
LLMs optimize for plausible next-token continuation, not verified truth, and general-purpose models like Gemini have no built-in guarantee of grounding in the app's actual computed data unless the agent is explicitly constrained to only restate/summarize values passed into its context.

**How to avoid:**
- Constrain the agent's role strictly to *explaining and summarizing the deterministic engine's own outputs* (the factor scores, backtest metrics, and price history already computed by the traditional pipeline) rather than letting it freely generate new "facts" (e.g. company news, fundamentals) it wasn't given in context.
- Pass all numeric facts (scores, RMSE, price levels) into the LLM's context explicitly and instruct it (via system prompt) to only reference numbers it was given, never to invent figures.
- Where the agent answers open-ended follow-up questions, clearly label agent responses as AI-generated commentary, distinct from the deterministic computed numbers shown elsewhere in the UI, so users can visually distinguish "this is a calculated fact" vs. "this is an AI's generated explanation."
- Consider a lightweight validation/guardrail step: if feasible, spot-check that any numeric claim the agent makes in its response matches a number actually present in the context it was given (simple string/number matching), and fall back to a generic response if it doesn't.

**Warning signs:**
Agent responses citing specific numbers, dates, or facts not present in the underlying computed data or retrieved news context; users reporting the agent said something inconsistent with the numbers shown elsewhere on the page.

**Phase to address:**
LLM agent integration phase — build context-grounding and labeling as part of the initial agent design, not as a later fix, since retrofitting grounding constraints onto an already-built freeform agent is harder than designing them in from the start.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Single train/test split instead of walk-forward validation | Faster to build, simpler code | Misleading/optimistic accuracy metrics shown to users; model may fail in production | Only during early local prototyping, never for user-facing accuracy numbers |
| No TTL on `st.cache_data` for price/news data | Fewer API calls, faster dev loop | Stale prices/predictions silently shown to users | Never for live price data; acceptable for static reference data (e.g. sector/ticker metadata) |
| Loading FinBERT/models without `st.cache_resource` during early prototyping | Simpler code while iterating on model logic | Memory/CPU blowup once deployed to 1GB Community Cloud | Only in local dev before deployment; must be fixed before shipping |
| Skipping graceful degradation for API failures (yfinance/NewsAPI/Gemini) | Faster to build happy-path features | App-wide crashes/error pages under normal free-tier rate-limit conditions | Never acceptable beyond an early internal prototype — free-tier limits will be hit in normal use, not just edge cases |
| Generic "not financial advice" footer without reviewing UI copy/LLM prompt language | Fast to add, checks the compliance box visually | Doesn't actually reduce legal exposure if product framing/LLM language remains directive | Never — framing must be addressed at the content/prompt level, not just a footer |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|-------------------|
| yfinance | Looping per-ticker requests without caching/backoff, especially across multi-asset scans | Bulk `yf.download()`, `st.cache_data(ttl=...)` wrapper, retry/backoff, graceful fallback UI |
| NewsAPI (free Developer tier) | Assuming free tier works the same in a deployed app as in local dev | Verify ToS production-use restriction; prefer Alpha Vantage News & Sentiment or another deployable-safe source; cache aggressively |
| Gemini API (free tier) | Treating daily/per-minute quota as effectively unlimited for a multi-user agent with multiple LLM calls per interaction | Cache LLM outputs, minimize agent tool-call round-trips, track usage server-side, degrade gracefully on 429 |
| Supabase (free tier) | Assuming the project stays live indefinitely with no traffic | Free projects pause after 7 days of *database* inactivity (not just no visits) — schedule a periodic lightweight query/ping, or expect to manually unpause before demos |
| HuggingFace/FinBERT | Downloading/loading the model repeatedly (e.g. on every prediction call or every session) instead of once per process | `st.cache_resource` for the pipeline/model object; lazy-load only when sentiment scoring is actually requested |
| Streamlit Community Cloud | Assuming local dev resource usage (CPU/RAM) transfers directly to the 1GB shared cloud tier | Profile memory under combined-model, multi-session load before considering a phase "done"; treat 1GB as a hard design constraint, not an afterthought |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Reloading FinBERT/XGBoost/Prophet models per request instead of caching | Slow page loads, high memory churn, occasional OOM errors | `st.cache_resource` for all trained/loaded model objects | Breaks almost immediately with more than a couple of concurrent users, or with FinBERT enabled |
| Fetching full price history for every asset in the universe on every recommendation scan | Recommendation page becomes slow, hits yfinance rate limits | Cache price data with sensible TTL; fetch only the asset universe subset actually needed per scan; consider a nightly batch refresh job instead of on-demand fetch-everything | Breaks once the asset universe (stocks+ETFs+crypto+gold+forex) grows past a handful of dozens of tickers scanned live per user session |
| Synchronous, sequential LLM calls per agent reasoning step | Slow agent responses (multi-second to 10s+ latency), quota burn from unnecessary tool-call round-trips | Minimize LangGraph tool-call hops; batch context into fewer, larger calls rather than many small ones | Breaks under Gemini free-tier RPM limits especially with 2+ concurrent users |
| No batching/pagination on Supabase reads for user history | Slow profile/history pages as usage data accumulates | Paginate history queries; index on user_id + timestamp | Noticeable once a user has months of prediction/recommendation history logged |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing API keys (Gemini, NewsAPI/Alpha Vantage, Supabase service role key) in source or committed `.streamlit/secrets.toml` | Key leakage via git history, quota theft/abuse on shared free-tier keys | Use Streamlit Cloud's secrets manager (`st.secrets`), never commit keys; use `.gitignore` for local secrets files |
| Relying on Supabase Row Level Security (RLS) being "on by default" | Any authenticated user could read/write other users' profiles/history if RLS policies aren't explicitly configured | Explicitly define and test RLS policies per table (profiles, recommendation history, chat history) before shipping multi-user auth |
| Passing raw user input directly into LLM prompts without sanitization | Prompt injection attempts via the "follow-up question" feature, potentially manipulating agent behavior or leaking system prompt/context | Constrain agent tool access, validate/sanitize free-text input, keep system prompt instructions robust against injection attempts |
| Using `st.cache_resource` for anything containing per-user secrets/session data | Cross-user data leakage as described in Pitfall 7 | Keep all per-user data in `st.session_state` or a properly-scoped Supabase query, never in a process-wide cached resource |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| Showing a single-number "accuracy" metric with no context on how it was computed | Users over-trust a metric that may be from a single, possibly favorable, test window | Show accuracy as a range/distribution from walk-forward folds, with a plain-language note on what it means and its limitations |
| Silent failures when a free-tier API (yfinance/NewsAPI/Gemini) is rate-limited | Users see a broken page or generic error with no explanation | Explicit, friendly degraded states ("Live prices temporarily unavailable, showing last cached data from [time]"; "AI explanation temporarily unavailable") |
| Burying the "not financial advice" disclaimer in a footer or one-time modal | Users may not internalize the educational framing, increasing both real-world risk to users and legal exposure to the project | Persistent, visible disclaimer on every prediction/recommendation view, and cautious, non-directive UI copy throughout |
| Presenting LLM commentary and deterministic computed numbers with the same visual weight/styling | Users can't tell what's a calculated fact vs. an AI-generated interpretation | Visually distinguish AI-generated text (e.g. a distinct panel/badge: "AI commentary") from the deterministic scoring/backtest numbers |

## "Looks Done But Isn't" Checklist

- [ ] **Backtested accuracy display:** Often built on a single train/test split rather than true walk-forward validation — verify the number shown is aggregated across multiple out-of-sample folds, not one lucky window.
- [ ] **Model caching:** Often "works" in a quick local demo but reloads FinBERT/XGBoost/Prophet on every rerun — verify with a memory/latency profile under repeated interactions, not just a single manual click-through.
- [ ] **Multi-user isolation:** Often looks fine when tested solo — verify with two simultaneous sessions (different browsers/incognito) that profiles, recommendation history, and agent chat never cross-contaminate.
- [ ] **API failure handling:** Often only tested on the happy path — verify the app degrades gracefully (not a crash/blank page) when yfinance, NewsAPI/Alpha Vantage, or Gemini return errors or rate-limit responses; simulate this deliberately (e.g. mock a 429).
- [ ] **"Not financial advice" framing:** Often reduced to a single footer disclaimer added late — verify every page that shows a prediction/recommendation/ranked list carries the disclaimer, and that no UI copy or LLM prompt uses directive "buy/sell/you should" language.
- [ ] **Deployed-environment API validity:** Often tested only in local dev — verify news/sentiment integration actually functions (or gracefully no-ops) once running on the real Streamlit Community Cloud URL, given NewsAPI free-tier's dev-only ToS restriction.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|-----------------|
| Lookahead bias discovered after models are "working" | HIGH | Audit every feature/label column for point-in-time correctness; rebuild the feature pipeline with explicit shifting; re-run all backtests and re-validate reported accuracy numbers before trusting any prior results |
| Single train/test split shipped instead of walk-forward | MEDIUM | Retrofit a walk-forward backtest harness around existing model training code; re-generate and re-display accuracy metrics; relatively contained since it's mostly a validation-layer change, not a full model rewrite |
| NewsAPI free tier found unusable post-deployment | LOW–MEDIUM | Swap to Alpha Vantage News & Sentiment (or another deployable-safe source) behind the same news-fetching interface; if sentiment is behind a feature flag/optional toggle already, this is a contained swap |
| Cross-user state leakage found in production | HIGH | Immediate: disable the affected feature/cached resource; audit all `st.cache_resource`/global usage for mutable per-user state; move affected state to `st.session_state`/Supabase; this is a trust-damaging bug if it reaches real users, so treat as urgent |
| Memory/resource-limit crashes on Streamlit Cloud after adding FinBERT | MEDIUM | Make sentiment scoring lazy/opt-in if not already; verify `st.cache_resource` usage; consider a smaller distilled sentiment model; profile and trim other memory usage (e.g. limit in-memory price history window) |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|----------------|
| Lookahead bias in feature/label construction | Data/feature pipeline phase (before model training) | Automated leakage smoke test: truncating raw data at date T must not change any feature computed for date ≤T |
| Single split vs. walk-forward validation | Model training/backtesting phase | Backtest report shows fold-by-fold metrics (mean ± std), not a single number |
| yfinance rate-limit exhaustion | Data ingestion pipeline phase | Load-test with simulated multi-asset, multi-user concurrent fetches; confirm caching/backoff prevents 429 cascades |
| NewsAPI free-tier deployment incompatibility | News/sentiment integration phase | Confirm news fetching actually works against the deployed Streamlit Cloud URL, not just local dev |
| Gemini free-tier quota exhaustion under multi-user load | LLM agent integration phase | Simulate 2-3 concurrent user sessions triggering agent calls; confirm graceful degradation, not raw 429 errors, once quota is near/exceeded |
| 1GB memory ceiling with FinBERT + multiple models | FinBERT/sentiment phase, re-verified at deployment/hardening phase | Memory profiling under combined-model, multi-session load stays comfortably under 1GB |
| `st.cache_resource`/`st.cache_data` misuse | Prediction-model phase (initial), Supabase auth/multi-user phase (re-verified) | Two-concurrent-session test confirms no cross-user data bleed; TTL confirmed on all live-data caches |
| Unlicensed investment advice framing | Earliest phase rendering any prediction/recommendation UI | Content/copy review confirms no directive language; disclaimer present on every relevant view |
| LLM hallucination / overconfident agent output | LLM agent integration phase | Spot-check agent responses against the numeric context it was given; verify visual distinction between AI commentary and computed facts |

## Sources

- [Look-Ahead Bias in Rolling Window Features](https://www.mhtechin.com/support/look-ahead-bias-in-rolling-window-features/)
- [Lookahead Bias in Machine Learning: Challenges and Solutions](https://fastercapital.com/content/Lookahead-Bias-in-Machine-Learning--Challenges-and-Solutions.html)
- [3 Common Time Series Modeling Mistakes You Should Know](https://towardsdatascience.com/3-common-time-series-modeling-mistakes-you-should-know-a126df24256f/)
- [Walk Forward Validation VS Train-Test Split - What to Choose?](https://abouttrading.substack.com/p/walk-forward-validation-vs-train)
- [Stock Prediction with ML: Walk-forward Modeling — The Alpha Scientist](https://alphascientist.com/walk_forward_model_building.html)
- [How To Backtest Machine Learning Models for Time Series Forecasting](https://machinelearningmastery.com/backtest-machine-learning-models-time-series-forecasting/)
- [Getting 429 error (rate-limit) — yfinance GitHub issue #2125](https://github.com/ranaroussi/yfinance/issues/2125)
- [Why yfinance Keeps Getting Blocked, and What to Use Instead](https://medium.com/@trading.dude/why-yfinance-keeps-getting-blocked-and-what-to-use-instead-92d84bb2cc01)
- [Rate Limits — Yahoo Finance data (Yahoo Inc. help docs)](https://help.yahooinc.com/datax/docs/rate-limits-1)
- [Pricing - News API](https://newsapi.org/pricing)
- [Best Free News APIs in 2026 (With Honest Limitations)](https://apitube.io/blog/post/best-free-news-apis-honest-limitations)
- [Rate limits | Gemini API | Google AI for Developers](https://ai.google.dev/gemini-api/docs/rate-limits)
- [What to do when a Streamlit Cloud Community App is hitting resource limits?](https://community.snowflake.com/s/article/What-to-do-when-a-Streamlit-Cloud-Community-App-is-hitting-resource-limits)
- [Manage your app - Streamlit Docs](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)
- [FAQ: This app has gone over its resource limits - Streamlit](https://discuss.streamlit.io/t/faq-this-app-has-gone-over-its-resource-limits/62973)
- [Caching overview - Streamlit Docs](https://docs.streamlit.io/develop/concepts/architecture/caching)
- [st.cache_resource - Streamlit Docs](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource)
- [Multi-user issue, session_state not unique for each user - Streamlit Community](https://discuss.streamlit.io/t/multi-user-issue-session-state-not-unique-for-each-user/44897)
- [st.session_state is shared across browsers/sessions/connections - streamlit/streamlit GitHub issue #5581](https://github.com/streamlit/streamlit/issues/5581)
- [ProsusAI/finbert · Hugging Face](https://huggingface.co/ProsusAI/finbert)
- [ProsusAI/finbert · AUTOMATED Model Memory Requirements](https://huggingface.co/ProsusAI/finbert/discussions/20)
- [The Ultimate Guide to Robo-Advisor Regulation in the U.S.](https://uslawexplained.com/robo-advisor)
- [SEC.gov | SEC Staff Issues Guidance Update and Investor Bulletin on Robo-Advisers](https://www.sec.gov/newsroom/press-releases/2017-52)
- [ARE ROBOTS GOOD FIDUCIARIES? REGULATING ROBO-ADVISORS UNDER THE INVESTMENT ADVISERS ACT OF 1940 - Columbia Law Review](https://www.columbialawreview.org/content/are-robots-good-fiduciaries-regulating-robo-advisors-under-the-investment-advisers-act-of-1940-2/)
- [The Complete Guide to Backtesting Pitfalls in Quantitative Trading](https://coriva.eu.org/en/backtesting-pitfalls/)
- [A Practical Guide To The Backtesting Mistakes That Kill Quant Strategies](https://hedgefundalpha.com/education/backtesting-mistakes-kill-quant-strategies-guide/)
- [Understanding the Risks AI Hallucinations Create for Businesses](https://natlawreview.com/article/ai-hallucinations-are-creating-real-world-risks-businesses)
- [LLM Hallucinations: What Are the Implications for Financial Institutions?](https://biztechmagazine.com/article/2025/08/llm-hallucinations-what-are-implications-financial-institutions)
- [Supabase Free Tier Limits in 2026: Hidden Pauses & Caps](https://www.itpathsolutions.com/supabase-free-tier-limits)
- [Billing FAQ | Supabase Docs](https://supabase.com/docs/guides/platform/billing-faq)

---
*Pitfalls research for: Quant recommendation & price-prediction platform (MarketMind)*
*Researched: 2026-07-14*
