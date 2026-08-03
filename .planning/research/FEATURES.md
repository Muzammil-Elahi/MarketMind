# Feature Research

**Domain:** Retail quant/fintech research and recommendation platform (multi-asset: stocks, ETFs, crypto, gold, forex) — free-tier, educational, non-brokerage
**Researched:** 2026-07-14
**Confidence:** MEDIUM (web-sourced, cross-checked across multiple competitor products; no primary-source pricing/ToS review of every competitor)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist on any research/recommendation product in this category. Missing these makes the product feel broken or untrustworthy, even if the "smart" parts work well.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Investor profile / risk questionnaire | Every robo-advisor and most research tools onboard with goals, time horizon, risk tolerance before showing recommendations (Wealthfront: 4 objective + 6 subjective questions; Betterment: goal-first). Users expect personalization to start here. | LOW | Already in PROJECT.md scope. Should map directly to the hybrid rec engine's factor weights — profile answers must visibly change output, or users perceive it as decorative. |
| Ranked asset list / screener | Core output of every competitor (Zacks #1-5 rank, Seeking Alpha Quant Rating, TipRanks Smart Score, Simply Wall St snowflake). Users expect a sortable/filterable list, not a single suggestion. | MEDIUM | Needs per-asset score + rank + short "why" tag visible in the list view, not just on drill-in. |
| Per-asset detail/drill-in page | All competitors let users click from the list into a dedicated page with fundamentals, chart, and score breakdown. | MEDIUM | This is where price prediction + sentiment + LLM explanation should live per PROJECT.md architecture. |
| Basic price chart with history | Baseline expectation for any finance app — users will bounce immediately if they can't see a price chart. | LOW | yfinance historical data + Plotly/Streamlit chart; cheap to build, high expectation cost if missing. |
| Watchlist / saved assets | Every research platform (Seeking Alpha, TipRanks, Morningstar) lets users save tickers to revisit. Without persistence, the app feels like a one-shot toy. | LOW-MEDIUM | Requires Supabase persistence layer already planned for auth — natural extension of the users table. |
| Score/rating transparency (why this score) | TipRanks Smart Score, Seeking Alpha Quant Rating, Simply Wall St snowflake all break the composite score into visible sub-factors. Users distrust unexplained single numbers. | MEDIUM | Directly informs the "traditional hybrid model must be interpretable, not just the LLM layer" requirement — the deterministic score itself needs a visible breakdown (factor scores), independent of the LLM explanation. |
| Educational/compliance disclaimer on every prediction/recommendation view | FINRA Rule 2214 requires investment-analysis tools to disclose hypothetical/non-guaranteed nature of projections; Rule 2111.03 safe-harbors educational content only if it avoids personalized security recommendations. Already a named PROJECT.md constraint. | LOW | Must appear on every rec list, every prediction chart, every LLM explanation — not just a footer on the homepage. Language pattern: "educational purposes only," "not personalized investment advice," "hypothetical, not a guarantee of future results." |
| Multi-user auth + persisted history | Any shared, multi-user product needs login and to remember prior state across sessions — already scoped via Supabase. | MEDIUM | Table stakes once the product is not personal-only, which PROJECT.md already commits to. |
| Asset search across asset classes | Users expect to type a ticker or name and find it regardless of whether it's a stock, crypto, or forex pair — competitors that silo asset classes (e.g., crypto-only or equity-only tools) feel limited compared to Morningstar/Simply Wall St style "any security" search. | LOW-MEDIUM | yfinance ticker normalization work (e.g. `EURUSD=X`, `BTC-USD`) needs a friendly search layer on top. |

### Differentiators (Competitive Advantage)

Features that set MarketMind apart from either pure-research tools (Simply Wall St, TipRanks) or pure-robo-advisors (Wealthfront) or pure-prediction tools (Tickeron). These should align with the Core Value: "recommendation and prediction work together as one pipeline."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Unified recommendation + prediction pipeline (one asset, one flow) | Competitors split these: TipRanks/Seeking Alpha do scoring/ranking but not multi-model forecasting; Tickeron/TrendSpider do prediction but not profile-driven cross-asset recommendation. Combining them into one coherent user journey (profile -> ranked list -> drill-in -> forecast -> explanation) is the stated core value and is not common in free tools. | HIGH | This is the product's central bet — architecture must keep the deterministic rec engine and prediction models loosely coupled but UI-unified. |
| Multi-model price forecasting with visible confidence intervals and backtested accuracy per model | Best-in-class AI prediction tools (Tickeron, TrendSpider, AltIndex) show confidence scores and published backtest accuracy (~70-75% claimed) with out-of-sample validation. Showing RMSE/directional accuracy/Sharpe per model (SMA, XGBoost, Prophet) side-by-side, with confidence intervals on the chart itself, is more rigorous than most free competitors, which usually show only a single black-box "score." | HIGH | Directly maps to existing PROJECT.md requirement. Differentiator specifically because it's multi-model and shows the accuracy honestly rather than a single opaque confidence number. |
| LLM agent reranking + plain-English investment thesis + follow-up Q&A | Fintech AI UX research is explicit that black-box AI predictions destroy trust — "if users can't figure out why the AI is suggesting something, they won't follow it." An LLM layer that explains the deterministic score in plain English, and answers "why is this ranked here" / "what changed" questions, directly addresses the #1 documented trust pitfall in this domain. Most competitors (Zacks, TipRanks) show numeric scores with generic canned explanations, not conversational, asset-specific reasoning. | HIGH | Must be clearly scoped as reranking/explaining a deterministic base score (per PROJECT.md decision), not as the source of truth — this also mitigates hallucination risk since the LLM is graded against a known-correct computation. |
| Optional sentiment layer (FinBERT news sentiment) feeding into prediction | Crypto research platforms (Santiment, Messari) treat sentiment as a first-class signal blended with on-chain/fundamental data; most free equity tools do not expose sentiment scoring transparently. Making sentiment an opt-in, visible input (not a black box) differentiates from tools that either ignore it or bury it. | MEDIUM-HIGH | Already scoped. Complexity driven by NewsAPI/Alpha Vantage free-tier rate limits and FinBERT inference cost on Streamlit Community Cloud's limited compute — caching is required, not optional (per PROJECT.md constraint). |
| Cross-asset-class unified experience (stocks + ETFs + crypto + gold + forex in one profile-driven flow) | Most retail tools specialize: Seeking Alpha/Zacks/Morningstar are equity/fund-focused; CoinGecko/Messari/Santiment are crypto-only. A single profile that recommends across all five asset classes with one consistent scoring and prediction methodology is uncommon at the free tier. | MEDIUM | Complexity is mostly in normalizing very different data behaviors (crypto trades 24/7, forex has different volatility regimes, gold is a single quasi-commodity) into one factor-scoring framework — flagged as a modeling risk, not just a UI one. |
| Backtested accuracy shown per user, per model, on real predictions (not just marketing claims) | Competitors' accuracy stats (Tickeron ~70%, AltIndex ~75%) are marketing claims computed by the vendor, opaque to the user. Showing the user their specific asset's backtest results (RMSE, directional accuracy, Sharpe) transparently, computed live, builds more credible trust than a vendor-wide percentage. | MEDIUM-HIGH | Already scoped as a requirement; the differentiator is transparency/specificity vs. generic vendor-level accuracy marketing. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create disproportionate regulatory, complexity, or trust risk for this product's stated scope (educational research tool, not a brokerage).

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Real trade execution / brokerage integration | Users naturally want to act on a recommendation immediately ("just let me buy it"). | Crosses into broker-dealer/investment-adviser regulation (SEC/FINRA), requires KYC/AML, custody, and liability far beyond an educational tool's scope; already explicitly out of scope in PROJECT.md. | Deep-link to the user's existing brokerage (e.g., open a prefilled trade in their broker's app/web via a plain URL) or simply display the ticker for the user to act on themselves — zero execution liability. |
| Specific "buy at $X, sell at $Y" trade signals with target prices/timing | Trading tools like Trade Ideas and some AI predictors give explicit entry/exit levels; users request this because it feels actionable. | This is the clearest line FINRA draws between "educational" and "personalized investment advice" (Rule 2111.03 safe harbor requires NOT recommending specific action on a specific security to a specific person) — doing this risks regulatory reclassification as investment advice. | Show probabilistic price ranges/confidence intervals and directional bias ("model suggests X% chance of upward movement over N days") framed as hypothetical model output, not a trade instruction — pairs naturally with the disclaimer requirement already in PROJECT.md. |
| Real-time streaming quotes / sub-minute updates | Users compare against trading platforms and expect live ticking prices. | yfinance free tier and Streamlit Community Cloud compute/uptime limits make true real-time infeasible without paid data (explicit PROJECT.md budget constraint); also encourages day-trading behavior misaligned with a research tool's educational framing. | Delayed/periodic refresh (e.g., cached with a visible "as of" timestamp) — standard pattern even paid retail tools use (most equity data is 15-min delayed on free tiers anyway). |
| Social/copy-trading features (follow other users' portfolios, copy trades) | Seeking Alpha's community model and TipRanks' "track the pros" angle show demand for social proof in this space. | Significant scope creep: needs its own moderation, reputation system, and potentially triggers different regulatory scrutiny (looks like a signal service); dilutes focus from the core rec+prediction pipeline that is the actual differentiator. | Defer entirely; if community signal is wanted later, expose aggregate/anonymized "what similar profiles are viewing" rather than individual-follow social features. |
| Full portfolio optimizer / walk-forward backtesting engine (PyPortfolioOpt, vectorbt-style) | Power users and "quant" positioning naturally invite requests for portfolio-level optimization (efficient frontier, rebalancing). | Already explicitly deferred in PROJECT.md — correctly, since it's a large orthogonal engineering effort (multi-asset covariance, constraints, rebalancing logic) that doesn't block validating the core recommend+predict loop. | Single-asset-at-a-time recommendation and prediction for v1; revisit portfolio-level optimization as a v2 differentiator once the core loop is validated. |
| LLM as the primary/sole recommendation engine (ask Gemini "what should I buy") | Feels like the simplest possible implementation — one prompt, no scoring pipeline. | Non-deterministic, unauditable, prone to hallucinated tickers/prices, and impossible to backtest or explain consistently — already explicitly rejected in PROJECT.md's key decisions. Also the most-cited fintech AI trust pitfall is "black box" reasoning; an LLM-only recommender is a black box by construction. | Keep the LLM strictly in the reranking/explanation/Q&A role on top of the deterministic factor+collaborative model, as already decided. |
| Guaranteed/marketed accuracy percentages ("94% accurate!") in UI copy or marketing | Competitors (AltIndex "75% accuracy") use this as a headline trust signal, so it's tempting to copy. | Backtested accuracy on historical data does not guarantee future performance; presenting a single flashy accuracy number without context is exactly the kind of overpromising that fintech UX research flags as trust-destroying once it's proven wrong in practice, and risks FINRA Rule 2214's requirement that projections be labeled hypothetical/non-guaranteed. | Show accuracy metrics (RMSE, directional accuracy, Sharpe) in context, per-model, per-asset, framed explicitly as backtested/historical with the required hypothetical-results disclaimer next to them. |

## Feature Dependencies

```
Investor Profile
    └──requires──> Auth + Persistence (Supabase)

Ranked Asset List (Hybrid Rec Engine)
    └──requires──> Investor Profile
    └──requires──> Factor/collaborative scoring pipeline

Per-Asset Drill-in Page
    └──requires──> Ranked Asset List (asset must be reachable from somewhere)
    └──requires──> Price History Data (yfinance)

Multi-Model Price Prediction
    └──requires──> Per-Asset Drill-in Page
    └──requires──> Price History Data (yfinance)
    └──requires──> Backtesting harness (walk-forward, no lookahead bias)

Backtested Accuracy Display
    └──requires──> Multi-Model Price Prediction
    └──requires──> Backtesting harness

Sentiment Layer (FinBERT)
    └──requires──> News data source (NewsAPI/Alpha Vantage)
    └──enhances──> Multi-Model Price Prediction (optional input, not required)

LLM Explanation Agent (rerank + Q&A)
    └──requires──> Ranked Asset List (needs a deterministic base score to rerank/explain)
    └──requires──> Score/rating transparency (factor breakdown the LLM can reference/ground its explanation in)
    └──enhances──> Multi-Model Price Prediction (can explain forecast + confidence interval in plain English too)

Watchlist
    └──requires──> Auth + Persistence (Supabase)
    └──enhances──> Ranked Asset List (save-from-list interaction)

Real Trade Execution ──conflicts──> Educational/Compliance Disclaimer framing
Specific Buy/Sell Target Prices ──conflicts──> FINRA educational safe-harbor (Rule 2111.03)
```

### Dependency Notes

- **Ranked Asset List requires Investor Profile:** the hybrid rec engine's factor weights and collaborative similarity need profile inputs (risk tolerance, sector prefs, capital) to produce a personalized ranking rather than a generic top-N list — this is the crux of "profile builder" being a true dependency, not decoration.
- **LLM Explanation Agent requires Score/rating transparency:** the agent needs to ground its plain-English thesis in the same visible factor breakdown a human sees, both to avoid contradicting the deterministic score and to make its explanations checkable/trustworthy (directly addresses the black-box trust pitfall).
- **Backtested Accuracy Display requires the backtesting harness (walk-forward, no lookahead bias):** this is a shared PROJECT.md non-negotiable constraint underlying both the prediction models and the accuracy metrics shown to users — build once, use for both.
- **Sentiment Layer enhances rather than requires Multi-Model Price Prediction:** PROJECT.md scopes it as optional ("user can optionally include"), so predictions must function correctly with sentiment off — plan the prediction pipeline's interface accordingly (sentiment as an additive feature column, not a required one).
- **Real Trade Execution / specific price targets conflict with the compliance/disclaimer framing:** including either would undermine the "educational tool" safe harbor the whole product's compliance posture depends on — these are correctly out of scope and should stay that way even as differentiators are added later.

## MVP Definition

### Launch With (v1)

Minimum viable product — matches PROJECT.md's Active requirements, reframed against competitor table-stakes findings.

- [ ] Investor profile builder (risk tolerance, time horizon, sector preferences, capital, holdings) — without this, the rec engine has nothing to personalize against
- [ ] Ranked recommendation list across stocks/ETFs/crypto/gold/forex via the hybrid (factor + collaborative) model — the core table-stakes output every competitor has, and the product's differentiator when combined with prediction
- [ ] Per-asset drill-in with price chart and multi-model prediction (SMA, XGBoost, Prophet) + confidence intervals — matches the "prediction" half of the core value prop
- [ ] Backtested accuracy display (RMSE, directional accuracy, Sharpe) per model — required for trust per fintech UX research, and already scoped
- [ ] LLM rerank + plain-English thesis on the recommendation list — the single biggest documented trust/differentiation lever found in research; without it, the product is just another numeric-score tool
- [ ] Compliance disclaimer on every recommendation and prediction view — non-negotiable per FINRA guidance and PROJECT.md constraint; must ship with v1, not bolted on later
- [ ] Multi-user auth + persisted profile/history (Supabase) — already required for the product to be shared at all
- [ ] Watchlist (save asset from list/drill-in) — table stakes, low complexity, natural extension of persistence layer already being built

### Add After Validation (v1.x)

Features to add once the core recommend+predict+explain loop is working and validated with real users.

- [ ] Sentiment layer (FinBERT news sentiment) as an opt-in prediction input — trigger: core prediction pipeline is stable and users are asking "why didn't it account for the news"
- [ ] LLM follow-up Q&A (conversational, not just initial thesis) — trigger: users engage with the initial LLM explanation and want to dig deeper; adds LangGraph conversational state on top of the existing rerank agent
- [ ] Expanded model set (LSTM, ARIMA, Linear Regression) — trigger: SMA/XGBoost/Prophet baseline is validated and users want higher accuracy or more model diversity to compare against

### Future Consideration (v2+)

Features to defer until the core product-market fit (does a profile-driven, explainable, multi-asset rec+prediction tool retain users) is established.

- [ ] Portfolio-level optimizer / walk-forward backtesting engine (PyPortfolioOpt, vectorbt) — defer because it's a large orthogonal build that doesn't validate the core single-asset loop first
- [ ] Cross-user aggregate signals ("similar profiles are viewing X") — defer because it requires enough user volume to be meaningful and risks looking like unlicensed signal-service behavior if not framed carefully
- [ ] Deep-link to brokerage for execution (not execution itself) — defer until the recommendation quality is validated enough that "send me to my broker" is a requested convenience, not a core need

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Investor profile builder | HIGH | LOW | P1 |
| Ranked recommendation list (hybrid engine) | HIGH | HIGH | P1 |
| Per-asset price chart | HIGH | LOW | P1 |
| Multi-model prediction + confidence intervals | HIGH | HIGH | P1 |
| Backtested accuracy display | HIGH | MEDIUM | P1 |
| LLM rerank + plain-English thesis | HIGH | HIGH | P1 |
| Compliance disclaimer | HIGH | LOW | P1 |
| Multi-user auth + persistence | HIGH | MEDIUM | P1 |
| Watchlist | MEDIUM | LOW | P1 |
| Sentiment layer (FinBERT) | MEDIUM | MEDIUM-HIGH | P2 |
| LLM follow-up Q&A | MEDIUM | MEDIUM | P2 |
| Expanded model set (LSTM/ARIMA/LinReg) | MEDIUM | MEDIUM | P2 |
| Portfolio optimizer | MEDIUM | HIGH | P3 |
| Cross-user aggregate signals | LOW | MEDIUM | P3 |
| Brokerage deep-link | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Seeking Alpha / TipRanks / Zacks / Simply Wall St / Morningstar | Wealthfront / Betterment | Tickeron / TrendSpider / AltIndex | Our Approach |
|---------|---|---|---|---|
| Personalized profiling | Minimal to none (screeners are self-directed, not profile-driven) | Deep (4-10 question risk questionnaires drive full allocation) | None (predictions are asset-specific, not user-specific) | Adopt robo-advisor-style profiling, but drive an asset ranking rather than a portfolio allocation |
| Composite scoring | Yes — single numeric/visual score per asset (Smart Score, Quant Rating, snowflake, #1-5 rank) | No (allocation-based, not per-security scoring) | Partial (confidence score per prediction, not a holistic asset score) | Combine composite factor+collaborative score (research-tool pattern) with per-prediction confidence intervals (prediction-tool pattern) |
| Price forecasting | No (fundamentals/ratings only, not price prediction) | No | Yes — core feature, with backtested accuracy marketing | Multi-model forecasting with per-model backtested metrics shown transparently, not a single vendor-level accuracy claim |
| Plain-English explanation | Generic templated commentary, not conversational | Minimal (allocation rationale, not per-security) | Rare/absent — mostly numeric outputs | LLM agent generates asset-specific thesis grounded in the visible factor score, plus follow-up Q&A |
| Sentiment/news integration | Partial (Seeking Alpha aggregates news, TipRanks tracks sentiment as one Smart Score input) | No | Rare | Opt-in FinBERT sentiment as a visible, toggleable input to prediction, not a buried sub-score |
| Multi-asset-class coverage | Mostly equities/funds; some (Morningstar) cover bonds | Equities/bonds/ETFs only, no crypto/forex/gold in one flow | Mostly equities/crypto separately, rarely combined | Single profile-driven flow spanning stocks, ETFs, crypto, gold, forex |
| Compliance framing | Standard "not investment advice" footers | Registered investment advisers (different regulatory posture, not directly comparable) | Mixed — some border on signal-service framing | Strict educational-only framing on every view per FINRA Rule 2214/2111.03 patterns, since this product is explicitly not a registered adviser |

## Sources

- [Which Is Best? Motley Fool vs Zacks vs Morningstar vs Seeking Alpha (WallStreetZen)](https://www.wallstreetzen.com/blog/motley-fool-vs-zacks-vs-morningstar-vs-seeking-alpha/) — MEDIUM confidence
- [Seeking Alpha vs. TipRanks (Wall Street Survivor)](https://www.wallstreetsurvivor.com/seeking-alpha-vs-tipranks/) — MEDIUM confidence
- [Simply Wall Street vs Seeking Alpha (Simply Wall St)](https://simplywall.st/vs/simply-wall-street-vs-seeking-alpha) — MEDIUM confidence
- [Seeking Alpha vs The Motley Fool vs Morningstar vs Zacks (stockanalysis.com)](https://stockanalysis.com/article/seeking-alpha-vs-motley-fool-vs-morningstar-vs-zacks/) — MEDIUM confidence
- [Best Robo-Advisors for Automated Investing 2026 (NerdWallet)](https://www.nerdwallet.com/investing/best/robo-advisors) — MEDIUM confidence
- [Wealthfront vs Betterment (Frec)](https://frec.com/resources/blog/wealthfront-vs-betterment-choosing-the-best-robo-advisor) — MEDIUM confidence
- [Wealthfront vs. Betterment (CNBC Select)](https://www.cnbc.com/select/wealthfront-vs-betterment/) — MEDIUM confidence
- [FINRA Rule 2214: Requirements for the Use of Investment Analysis Tools](https://www.finra.org/rules-guidance/rulebooks/finra-rules/2214) — HIGH confidence (primary regulatory source)
- [FINRA Rule 2111 Suitability FAQ](https://www.finra.org/rules-guidance/key-topics/suitability/faq) — HIGH confidence (primary regulatory source)
- [FINRA Investor Alert: Automated Investment Tools](https://www.finra.org/investors/insights/automated-investment-tools) — HIGH confidence (primary regulatory source)
- [What is the Most Accurate AI Stock Predictor? (WallStreetZen)](https://www.wallstreetzen.com/blog/best-ai-stock-predictor/) — MEDIUM confidence
- [Best AI Stock Prediction Tools for 2026 (Intellectia)](https://intellectia.ai/blog/best-ai-stock-prediction-tool) — MEDIUM confidence
- [Algorithm Performance Backtest (Intratio)](https://intratio.com/en/backtest/) — MEDIUM confidence
- [Santiment — Crypto Research, Data, Tools](https://santiment.net/) — MEDIUM confidence
- [Best Crypto Analysis Tools in 2026 (Coin Bureau)](https://coinbureau.com/review/crypto-research-tools) — MEDIUM confidence
- [Messari Sentiment API Docs](https://docs.messari.io/api-reference/endpoints/signal/sentiment/overview) — MEDIUM-HIGH confidence (vendor docs)
- [How UX Impacts Trust and Growth in AI FinTech Products (ProCreator)](https://procreator.design/blog/how-ux-impacts-trust-in-ai-fintech-products/) — MEDIUM confidence
- [Fintech UX Best Practices 2026 (Eleken)](https://www.eleken.co/blog-posts/fintech-ux-best-practices) — MEDIUM confidence
- [FinAI: Simplifying Stock Research with AI — UX Case Study (Medium)](https://medium.com/@sd9242773/finai-simplifying-stock-research-with-ai-a-ux-case-study-34addb1f682d) — LOW-MEDIUM confidence (single case study, not a competitor product)

---
*Feature research for: Retail quant/fintech recommendation and price-prediction platform*
*Researched: 2026-07-14*
