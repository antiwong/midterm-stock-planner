# Sentiment DuckDB Integration Proposal

> **Date**: 2026-03-23
> **Context**: The SentimentPulse crawler (Mac) writes to `sentimentpulse.db` (DuckDB) which syncs to the Hetzner server. The midterm-stock-planner reads this DB for sentiment data. Currently only ~20% of the available data is being used.

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

## Questions for Discussion

1. **Feature engineering**: Should we add sentiment features to the ML model, or keep sentiment in the trigger layer only? The regression tests showed sentiment had zero Sharpe impact previously — but that was with the old CSV data (limited to composite_score). Options flow and insider data are fundamentally different signals.

2. **Deep analysis rendering**: Should deep_analysis HTML be shown as a dedicated tab, or inline within the ticker detail page? The HTML is styled for WordPress — may need CSS adaptation.

3. **Social data reliability**: ApeWisdom/StockTwits/X data can be noisy. Should we use it as features directly, or only as confirmation signals in the trigger layer?

4. **Earnings proximity**: The `earnings_days_to` field enables pre-earnings strategies (drift detection, vol expansion). Is this something the model should learn, or should it be a separate trading rule?

5. **Crawl quality gates**: Should we surface crawl health prominently (quality degradation alerts), or keep it as a background monitoring metric?

---

## Files That Would Change

### Backend (API)
- `src/api/routers/sentiment.py` — overview, news, new deep_analysis endpoint
- `src/sentiment/sentiment_adapter.py` — expose more columns for feature pipeline
- `src/features/engineering.py` — add options/insider/social features
- `src/trigger/sentiment_trigger.py` — additional gates

### Frontend
- `myfuture/src/pages/Sentiment.tsx` — overview expansion, new Deep Analysis tab, enhanced news tab
- `myfuture/src/api/client.ts` — new types for expanded data

### Config
- `config/config.yaml` — new feature flags for sentiment features in ML model
