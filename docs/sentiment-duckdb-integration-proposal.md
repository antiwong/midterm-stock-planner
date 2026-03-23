# Sentiment DuckDB Integration Proposal

> **Date**: 2026-03-24 (updated)
> **Status**: Phase 0-3, 5-6 COMPLETE. Phase 4 deferred.
> **Context**: The SentimentPulse crawler (Mac) writes to `sentimentpulse.db` (DuckDB) which syncs to the Hetzner server. The midterm-stock-planner reads this DB for sentiment data.

---

## Current State

### What's in DuckDB (9 tables, ~25K rows)

| Table | Rows | Description |
|-------|------|-------------|
| `sentiment_features` | 763 | Per-ticker daily aggregate scores (86 columns) |
| `articles` | 24,090 | Every article fetched with per-article LLM scores |
| `deep_analysis` | 124 | Gemini Pro narrative HTML for flagged tickers |
| `crawl_runs` | 22 | Per-crawl metadata and quality metrics |
| `moby_picks` | 9 | Moby weekly analyst picks with thesis |
| `moby_news` | 36 | Moby weekly news articles |
| `feedback` | 0 | Actual returns (will populate over time) |
| `trigger_log` | 0 | Trigger evaluations (will populate over time) |
| `weight_history` | 0 | Source weight recalibration records |

### What we currently use vs what's available

**sentiment_features (86 columns — using ~16)**

Used:
- `composite_score`, `signal_breadth`, `signal_conviction`
- `llm_score`, `finnhub_score`, `eodhd_score`
- `headline_count`, `source_count`, `buzz_ratio`, `confidence`
- `sentiment_regime`, `market_regime`, `market_vix`, `market_spy_5d`
- `options_pcr`, `insider_signal`
- `analyst_consensus`, `analyst_consensus_score`

NOT used (~50 columns):

| Category | Unused Columns | What They Tell Us |
|----------|---------------|-------------------|
| **Individual Source Scores** | `finnhub_social_score`, `av_score`, `massive_score`, `marketaux_score`, `fmp_social_score` | Which sources agree/disagree — source divergence is a signal itself |
| **Social/Retail Sentiment** | `stocktwits_bullish_pct`, `stocktwits_message_volume`, `stocktwits_tagged_total` | StockTwits retail sentiment (self-tagged bullish/bearish) |
| **Reddit/ApeWisdom** | `apewisdom_mentions`, `apewisdom_rank`, `apewisdom_rank_change`, `apewisdom_upvotes`, `apewisdom_mention_ratio`, `apewisdom_spike_flag` | Reddit retail attention — mention spikes often precede moves |
| **X/Twitter** | `x_social_score`, `x_post_count_24h`, `x_high_engagement_flag`, `x_high_engagement_direction` | Institutional + retail social commentary |
| **Options Flow** | `iv_percentile`, `iv_skew`, `iv_current`, `iv_rank`, `options_pcr_30d`, `options_sentiment_signal`, `unusual_options_flag`, `unusual_options_direction`, `dark_pool_volume`, `options_data_available` | Smart money positioning — unusual options activity is one of the strongest leading indicators |
| **Google Trends** | `trends_interest_7d`, `trends_interest_30d`, `trends_7d_change`, `trends_spike_flag` | Search attention often leads price moves by 1-3 days |
| **Insider Activity** | `insider_cluster_flag`, `insider_net_30d`, `insider_buy_count_30d` | Insider cluster buys (3+ insiders buying within 30d) are historically strong signals |
| **Signal Quality** | `conviction_asymmetry`, `source_agreement`, `organic_score`, `propagation_weight`, `propagation_flag`, `propagation_source`, `has_primary_source` | Reliability of the composite signal — high source_agreement + organic_score = trustworthy signal |
| **Price Divergence** | `price_return_5d`, `price_divergence`, `divergence_direction` | Sentiment vs price disagreement — contrarian indicator |
| **Forward Events** | `forward_event_detected`, `forward_event_type`, `forward_event_date` | Upcoming catalysts: earnings, product launches, FDA decisions |
| **Analyst Actions** | `analyst_action_detected`, `analyst_firm`, `analyst_action_type`, `segment_focus` | Sell-side upgrades/downgrades with specific firm names |
| **Earnings** | `earnings_date`, `earnings_days_to`, `earnings_season_flag`, `eps_surprise_pct`, `report_hour` | Earnings proximity and historical surprise data |
| **Regime** | `market_confidence_mult`, `sentiment_regime_encoded`, `buzz_volume` | Pre-computed regime multipliers |
| **Deep Analysis** | `deep_analysis_html` | Pointer to Gemini-generated narrative in deep_analysis table |

**articles (27 columns — using ~5)**

Used: `headline`, `source`, `sentiment`, `date`, `ticker`

NOT used:
- `summary` — article summary (up to 1000 chars)
- `credibility_tier` / `credibility_weight` — Reuters (1.0) vs Reddit (0.4) vs sponsored (0.0)
- `one_line` — LLM one-sentence summary
- `category` — earnings / macro / product / policy / competition / management
- `impact_horizon` — immediate / short_term / medium_term
- `conviction_asymmetry` — score asymmetry within article
- `headline_body_agreement` — does headline match article body?
- `is_sponsored` — detected as PR/sponsored?
- `analyst_firm` / `analyst_action` — named analyst firm + action (upgrade/downgrade/initiate)
- `segment_focus` — specific business segment mentioned
- `products_mentioned` — specific products
- `forward_event_detected/type/date` — forward-looking events in this article

**deep_analysis (8 columns — completely unused)**

124 Gemini Pro narrative analyses for flagged tickers. Each contains:
- Full HTML analysis with themes, risks, catalysts, contrarian view
- Trigger reason (why Layer 2 was activated)
- Associated composite score and regime

**crawl_runs (17 columns — completely unused)**

Crawl health metrics: duration, articles fetched/filtered, scoring failures, quality gate pass rate.

---

## Proposed Changes

### 1. Sentiment Overview — Full Signal Dashboard

**Current**: Shows composite score, breadth, conviction, regime, analyst score, and Moby rating per ticker.

**Proposed**: Group data into signal categories per ticker:

```
AAPL — Composite: +0.05 | Breadth: 0.43 | Conviction: +0.02 | Regime: NOISE
  Sources:     LLM +0.08, Finnhub +0.03, EODHD +0.05, AV +0.02, Massive -0.01
  Social:      StockTwits 62% bullish (1,247 msgs) | Reddit #8 (↑3) | X: 45 posts
  Options:     PCR 0.85 | IV 42nd pctl | Skew -0.12 | ⚠️ Unusual calls detected
  Insiders:    Net +$2.3M (30d) | 3 buyers | ⚠️ Cluster buy flag
  Events:      Earnings in 12 days (Apr 24, after-hours) | EPS surprise +4.2% last Q
  Divergence:  Price -2.1% (5d) vs Sentiment +0.05 → CONTRARIAN signal
  Analyst:     Goldman Sachs upgrade (Mar 20) | Consensus: Strong Buy (1.21)
  Trends:      7d interest 78 | 30d interest 65 | +20% change | ⚠️ Spike flag
  Quality:     Source agreement 0.72 | Organic score 0.85 | Has primary source ✓
  Moby:        Overweight | Target $225 (+23%) | "Amazon's Not Broken..."
```

**API changes**: The `/sentiment/overview` endpoint would return all these fields nested by category. The frontend would render them as expandable sections or a detail panel.

### 2. News Tab — Credibility-Weighted, LLM-Enhanced

**Current**: Shows headline, source, date, raw sentiment score.

**Proposed**:
- Show `credibility_tier` badge (Tier 1 = gold, Tier 4 = gray)
- Show `one_line` LLM summary instead of (or alongside) headline
- Show `category` tag (earnings / macro / product / policy)
- Show `impact_horizon` (immediate / short-term / medium-term)
- Filter by credibility tier, category, impact horizon
- Flag articles where `headline_body_agreement = false` (clickbait)
- Highlight articles with `analyst_action` (upgrade/downgrade)
- Show `forward_event_type` when detected

**Source credibility breakdown** (new section):
```sql
SELECT source, credibility_tier,
       COUNT(*) as articles,
       ROUND(AVG(sentiment), 3) as avg_sentiment
FROM articles
WHERE ticker = 'AAPL' AND date = current_date
GROUP BY source, credibility_tier;
```

### 3. Deep Analysis Tab (NEW)

**Current**: Does not exist.

**Proposed**: New tab "Deep Analysis" showing Gemini Pro narrative HTML for flagged tickers. These are the same analyses published to the WordPress blog but now available directly in the dashboard.

Content per ticker:
- Full HTML narrative (themes, risks, catalysts, contrarian view)
- Why it was flagged (trigger_reason: top mover, divergence, unusual options)
- Composite score and regime at time of analysis
- Article count analyzed

Only ~10-20 tickers per crawl get deep analysis (the interesting ones), so this is a curated, high-value view.

### 4. Crawl Health Section

**Current**: No visibility into crawl quality.

**Proposed**: Small status card on Sentiment page showing:
- Last crawl time and duration
- Tickers scored vs total attempted
- Articles fetched vs filtered (quality gate)
- Scoring failures
- Market regime at crawl time (VIX, SPY 5d)

```sql
SELECT run_id, started_at, duration_s, tickers_scored, articles_total,
       scoring_failures, market_regime, market_vix
FROM crawl_runs ORDER BY started_at DESC LIMIT 1;
```

### 5. Feature Engineering — ML Model Integration

**Current**: The ML model uses `composite_score` via the `sentiment_adapter.py` → `engineering.py` pipeline. The trigger layer uses a subset of signals.

**Proposed**: Add these as features to the LightGBM model:

| Feature | Column(s) | Rationale |
|---------|-----------|-----------|
| Options flow | `options_pcr`, `iv_percentile`, `unusual_options_flag` | Smart money positioning is one of the strongest alpha signals |
| Insider activity | `insider_cluster_flag`, `insider_net_30d` | Insider cluster buys historically predict 6-12 month outperformance |
| Social momentum | `apewisdom_rank_change`, `stocktwits_bullish_pct`, `trends_7d_change` | Retail attention acceleration |
| Signal quality | `source_agreement`, `conviction_asymmetry` | High agreement = reliable signal |
| Divergence | `price_divergence` (binary), `divergence_direction` | Contrarian signals |
| Earnings proximity | `earnings_days_to`, `eps_surprise_pct` | Pre-earnings drift, post-earnings momentum |

This would expand the feature set from ~20 price/technical features to ~30 with sentiment enrichment.

**Important**: These features need the same walk-forward validation as other features to confirm they help Sharpe (some may hurt, like the RSI/momentum findings from the regression tests).

### 6. Trigger Layer Enhancement

**Current trigger fires on**: composite_score thresholds + regime multiplier.

**Proposed additional gates**:
- Block propagated-only signals (`propagation_flag=True` AND `has_primary_source=False`)
- Boost conviction when `insider_cluster_flag=True`
- Reduce conviction when `source_agreement < 0.3` (sources disagree)
- Flag `unusual_options_flag` as confirmation/contradiction of sentiment direction
- Use `conviction_asymmetry` to detect lopsided signal (all from one source type)

---

## Implementation Priority

| Priority | What | Impact | Effort |
|----------|------|--------|--------|
| **P1** | Sentiment Overview — full signal dashboard | High — makes all data visible | Medium — API + frontend |
| **P1** | Deep Analysis tab | High — 124 Gemini narratives unused | Low — just render HTML |
| **P2** | News tab — credibility + LLM summaries | Medium — better article quality | Medium — API + frontend |
| **P2** | Feature engineering — options/insider/social | High — potentially improves model | Medium — need regression validation |
| **P3** | Trigger layer gates | Medium — reduces false signals | Low — config + logic |
| **P3** | Crawl health section | Low — operational visibility | Low — simple query |

---

## Data Freshness

- Crawler runs 4x/day on the Mac (00:00, 06:00, 12:00, 18:00 SGT) + post-close US crawl (4:30 AM SGT Tue-Sat)
- DuckDB syncs to Hetzner every 30 min (once rsync cron is set up — **pending**)
- Data is 4 days old right now (Mar 20-23) with 763 sentiment_features rows across 372 tickers
- Articles table has 24,090 entries across 22 crawl runs

---

## Decisions Made

1. **Feature engineering**: DECIDED — Sentiment stays in trigger layer ONLY. `use_sentiment: false` is permanent. Regression tests proved sentiment degrades cross-sectional Sharpe (-0.18 to -0.28). The ranker answers "which stocks?" while sentiment answers "is now the right time?" — different questions.

2. **Deep analysis rendering**: DECIDED — Dedicated tab + expandable panel link. CSS scoping handled by prose classes.

3. **Social data reliability**: DECIDED — ApeWisdom is in trigger layer as confirmation signal (spike flag). StockTwits/X have 0% coverage — hidden until data flows.

4. **Earnings proximity**: DECIDED — Flagged in trigger reasoning only (not a gate). `earnings_days_to` shown in events section when within 7 days.

5. **Crawl quality gates**: DECIDED — Status bar at top of Sentiment page (green/yellow/red).

---

## Implementation Status (2026-03-24)

| Phase | Status | Details |
|-------|--------|---------|
| Phase 0: Validation | DONE | 29 BUILD, 4 STUB, 23 HIDE columns |
| Phase 1: Trigger | DONE | DuckDB reader, propagation gate, conviction asymmetry, insider cluster, earnings flag |
| Phase 2: API | DONE | 4 new endpoints: full ticker, deep analysis (recent + single), crawl health |
| Phase 3: Overview | DONE | Expandable detail panels with all signal categories |
| Phase 4: News | DEFERRED | Current news tab works; credibility badges P2 |
| Phase 5: Deep Analysis | DONE | Tab with 20 Gemini narrative cards |
| Phase 6: Crawl Health | DONE | Status bar with tickers/articles/failures/regime |

---

## DuckDB Usage Audit (2026-03-24)

### Reads from DuckDB (10 endpoints)

| Endpoint / Component | DuckDB Table(s) | What It Shows |
|---------------------|-----------------|---------------|
| `GET /sentiment/overview` | `sentiment_features` | Per-ticker composite, breadth, conviction, regime |
| `GET /sentiment/overview/full/{ticker}` | `sentiment_features` + `deep_analysis` + `moby_picks` | All 86 columns grouped by category |
| `GET /sentiment/blog` (SentimentPulse tab) | `sentiment_features` | Full daily feature set per ticker |
| `GET /sentiment/trend` | `sentiment_features` | Historical composite_score time series |
| `GET /sentiment/trend/multi` | `sentiment_features` | Multi-ticker trend comparison |
| `GET /sentiment/news` | `articles` | 24K articles with LLM scores |
| `GET /sentiment/deep-analysis/recent` | `deep_analysis` | 20 most recent Gemini narratives |
| `GET /sentiment/deep-analysis/{ticker}` | `deep_analysis` | Full HTML analysis for one ticker |
| `GET /sentiment/crawl-health` | `crawl_runs` | Last 5 crawl run quality metrics |
| `GET /moby/analysis` | `moby_picks` | Moby weekly picks with thesis |
| `GET /moby/news` | `moby_news` | Moby weekly news articles |
| Trigger layer (`sentiment_trigger.py`) | `sentiment_features` (via adapter) | Entry timing signals |

### Still reads from CSV (5 endpoints) — Migration Plan

| Endpoint | CSV File | Rows | Why CSV | Migration Owner |
|----------|----------|------|---------|----------------|
| `GET /sentiment/analyst` | `analyst_recommendations.csv` | 388 (97 tickers) | Downloaded by daily routine from Finnhub API | **midterm-stock-planner** |
| `GET /sentiment/insiders` | `insider_transactions.csv` | 49,698 (262 tickers) | Downloaded by daily routine from Finnhub API | **midterm-stock-planner** |
| `GET /sentiment/earnings` | `earnings_surprises.csv` | 388 (97 tickers) | Downloaded by daily routine from Finnhub API | **midterm-stock-planner** |
| `GET /ticker/{ticker}` (detail page) | `news.csv`, `analyst_recommendations.csv`, `earnings_surprises.csv` | Various | Ticker detail page reads multiple CSVs | **midterm-stock-planner** |
| `GET /earnings/` (calendar) | `earnings_surprises.csv` | 388 | Earnings calendar page | **midterm-stock-planner** |

**Migration approach**: The daily routine's `_refresh_all_data()` step downloads these CSVs from Finnhub. Add a step to also write them into DuckDB tables (new tables: `analyst_recommendations`, `insider_transactions`, `earnings_surprises`). Then update the API routers to read from DuckDB. Beads task: `midterm-stock-planner-p5i`.

### Known data gaps

| Column | Coverage | Issue | Owner |
|--------|----------|-------|-------|
| `eodhd_score` | 0% (all null) | Crawler fetches EODHD but doesn't write score to DuckDB | **sentimental_blogs** (beads: `midterm-stock-planner-ahy`) |
| `finnhub_score` | 0% | Same issue — individual source scores not populated | **sentimental_blogs** |
| `finnhub_social_score` | 0% | Social score not populated | **sentimental_blogs** |
| `stocktwits_bullish_pct` | 0% | StockTwits source not writing to DuckDB | **sentimental_blogs** |
| `x_social_score` | 0% | X/Twitter not configured (needs xAI API) | **sentimental_blogs** |
| `trends_*` | 0% | Google Trends not writing to DuckDB | **sentimental_blogs** |
| `dark_pool_volume` | 0% | Not implemented | Future |
| `iv_percentile` | 0% | Options IV percentile not populated (iv_skew IS populated at 94%) | **sentimental_blogs** |

---

## Column Definitions

### Core Metrics

| Column | Range | What It Means |
|--------|-------|---------------|
| **Composite Score** | -1.0 to +1.0 | Credibility-weighted blend of ALL sentiment sources. Positive = bullish consensus, negative = bearish. Computed by weighting each source by its credibility tier (Reuters=1.0, Reddit=0.4). |
| **Signal Breadth** | 0.0 to 1.0 | Fraction of data sources that had data for this ticker. 0.5 = half the sources contributed. Higher = more reliable signal. |
| **Signal Conviction** | -1.0 to +1.0 | `composite_score × signal_breadth`. Penalizes thin coverage. A +0.4 score from 3/14 sources has lower conviction than +0.3 from 12/14 sources. This is the primary trigger metric. |
| **Sentiment Regime** | MOMENTUM / CONTRARIAN / UNCERTAINTY / NOISE | Classified based on score consistency, buzz volume, and price action. MOMENTUM = sentiment and price agree. CONTRARIAN = they disagree (potential reversal). |
| **Confidence** | high / medium / low | LLM's self-assessed confidence in the composite score. Based on article quality and consistency. |

### Source Scores

| Column | Range | What It Means |
|--------|-------|---------------|
| **LLM Score** | -1.0 to +1.0 | Gemini Flash's article-level sentiment scoring, aggregated. The "smartest" source — reads article body, not just headline. |
| **Finnhub Score** | -1.0 to +1.0 | Finnhub's built-in sentiment API. Currently 0% populated — needs sentimental_blogs fix. |
| **EODHD Score** | -1.0 to +1.0 | EODHD's alternative sentiment. Currently 0% populated — needs sentimental_blogs fix. |
| **Massive/AV/MarketAux** | -1.0 to +1.0 | Other news API sentiment scores. Massive has 37% coverage. |

### Options Flow

| Column | What It Means |
|--------|---------------|
| **Options PCR** | Put/Call ratio. >1.0 = more puts (bearish), <1.0 = more calls (bullish). 60% coverage. |
| **IV Skew** | Implied volatility skew. Negative = puts more expensive (market hedging). 94% coverage. |
| **Unusual Options** | Flag for unusual sweep orders detected. Currently 0% — needs fix. |

### Social / Retail

| Column | What It Means |
|--------|---------------|
| **ApeWisdom Mentions** | Reddit mention count across WallStreetBets, stocks, investing. 100% coverage. |
| **ApeWisdom Rank** | Rank by mention count. #1 = most discussed ticker on Reddit. |
| **ApeWisdom Spike** | Flag when mentions spike >2σ above 30-day average. 98% coverage. |

### Insider Activity

| Column | What It Means |
|--------|---------------|
| **Insider Cluster Flag** | 3+ insiders buying within a 30-day window. Historically one of the strongest mid-term signals. 52% coverage. |
| **Insider Net 30d** | Net dollar value of insider buys minus sells over 30 days. Negative = more selling. 70% coverage. |
| **Insider Buy Count** | Number of distinct insider buyers in 30 days. |

### Signal Quality

| Column | What It Means |
|--------|---------------|
| **Source Agreement** | Standard deviation of source scores. Low (< 0.15) = sources agree. High (> 0.30) = sources disagree — less reliable. 90% coverage. |
| **Conviction Asymmetry** | Whether bullish or bearish evidence dominates. High positive = mostly bullish articles. 36% coverage. |
| **Organic Score** | Composite excluding propagated/supply-chain signals. Only articles directly about this ticker. 90% coverage. |

### Analyst

| Column | What It Means |
|--------|---------------|
| **Analyst Action Detected** | Whether a named analyst firm issued an upgrade/downgrade/initiation. 33% coverage. |
| **Analyst Consensus** | Aggregated consensus: strong_buy, buy, hold, sell, strong_sell. |
| **Analyst Consensus Score** | Numeric score from consensus. Higher = more bullish. |

---

## Files Changed (Final)

### Backend (API)
- `src/api/routers/sentiment.py` — 4 new DuckDB endpoints + overview reads DuckDB
- `src/api/routers/moby.py` — reads from DuckDB moby_picks/moby_news
- `src/sentiment/sentiment_adapter.py` — DuckDB-only reader (no CSV fallback)
- `src/sentiment/duckdb_reader.py` — low-level DuckDB reader
- `src/trigger/sentiment_trigger.py` — enriched with DuckDB signals
- `src/features/engineering.py` — sentiment REMOVED from ML model (Rule 1)
- `scripts/daily_routine.py` — recommendation generation step added
- `scripts/moby_to_duckdb.py` — Moby MD report parser

### Frontend
- `myfuture/src/pages/Sentiment.tsx` — expandable detail panels, Deep Analysis tab, crawl health bar
- `myfuture/src/components/MarkdownContent.tsx` — markdown rendering with keyword highlights
- `myfuture/src/components/PortfolioCard.tsx` — sp500/clean_energy/etfs support
- `myfuture/src/hooks/useActiveWatchlists.ts` — dynamic watchlist hook
- `myfuture/src/pages/RealtimeMonitoring.tsx` — crash fix
- `myfuture/src/pages/RecommendationTracking.tsx` — filter fix
- 5 pages updated to use dynamic watchlists
