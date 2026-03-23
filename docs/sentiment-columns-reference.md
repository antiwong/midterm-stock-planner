# Sentiment Data Reference

> **Source**: DuckDB `sentimentpulse.db` — synced from SentimentPulse crawler (Mac) every 30 minutes.
> **Last updated**: 2026-03-24
> **Tables**: 9 (sentiment_features, articles, deep_analysis, crawl_runs, moby_picks, moby_news, feedback, trigger_log, weight_history)

---

## How Sentiment Is Used

```
SentimentPulse Crawler (Mac)
    ↓ writes to DuckDB (7 core tables)
    ↓ rsync every 30 min
Hetzner Server (sentimentpulse.db)
    ↓
    ├── Sentiment API → Dashboard (overview, trends, deep analysis)
    ├── Trigger Layer → Entry timing gates (buy/hold/sell decisions)
    └── Moby Tables → Analyst picks + weekly news
```

**Key architectural rule**: Sentiment data goes into the **trigger layer** only, NOT the LightGBM cross-sectional ranker. The ranker answers "which stocks are relatively better?" — sentiment answers "is now the right moment?" These are different questions, and mixing them degraded Sharpe by -0.18 to -0.28 in regression tests. `use_sentiment: false` is permanent.

---

## Dashboard Columns Explained

### Overview Table

| Column | Range | What It Means | How It's Computed |
|--------|-------|---------------|-------------------|
| **Composite** | -1.0 to +1.0 | Overall sentiment score across all sources | Credibility-weighted average: Reuters/SEC filings (weight 1.0) → Finnhub/Alpha Vantage (0.8) → Reddit/StockTwits (0.4) → sponsored content (0.0). Positive = bullish consensus, negative = bearish. |
| **Breadth** | 0.0 to 1.0 | Data coverage — what fraction of sources contributed | `sources_with_data / total_sources_attempted`. Example: 7 out of 14 sources = 0.50. Higher breadth = more reliable signal. Low breadth means the score is based on thin data. |
| **Conviction** | -1.0 to +1.0 | Actionable signal strength | `composite_score × signal_breadth`. Penalizes thin coverage. A +0.40 composite from 3/14 sources gives conviction of +0.09. A +0.20 composite from 12/14 sources gives conviction of +0.17. **This is the primary metric the trigger layer uses.** |
| **News (7d)** | -1.0 to +1.0 | News sentiment average over 7 days | Same as composite but specifically from news article sources (Finnhub, Alpha Vantage, Massive, RSS feeds). |
| **Analyst** | 0.0 to ~2.0 | Sell-side consensus score | Derived from Finnhub analyst recommendations. Weighted: Strong Buy (2.0), Buy (1.5), Hold (1.0), Sell (0.5), Strong Sell (0.0). Higher = more bullish consensus. |
| **EODHD** | -1.0 to +1.0 | Alternative sentiment from EODHD API | Independent sentiment score from EODHD data provider. Currently **0% populated** due to a crawler bug (beads: `midterm-stock-planner-ahy`). |
| **Articles** | count | Number of articles analyzed | Total articles fetched and scored for this ticker in the last 7 days. More articles = more data points for the composite. |

### Expandable Detail Panel (click a ticker row)

#### Core Signal
| Field | What It Means |
|-------|---------------|
| **Sentiment Regime** | MOMENTUM (sentiment + price agree), CONTRARIAN (they disagree — potential reversal), UNCERTAINTY (mixed signals), NOISE (insufficient signal) |
| **Market Regime** | NORMAL, ELEVATED (VIX 20-30), HIGH_ANXIETY (VIX >30), FEAR. Based on VIX + SPY 5-day return. |
| **Confidence** | LLM's self-assessed confidence: high (consistent articles, clear direction), medium, low (contradictory or sparse). |
| **Headlines** | Number of articles from all sources for this ticker. |
| **Sources** | Number of distinct data sources that contributed (out of ~14 possible). |

#### Source Scores
Individual sentiment scores from each data provider. Shows which sources agree vs disagree.

| Source | What It Is |
|--------|-----------|
| **LLM** | Gemini Flash article-level scoring — reads full article body, not just headlines. The "smartest" source. |
| **Finnhub** | Finnhub's built-in news sentiment API. |
| **Massive** | Polygon/Massive news sentiment with reasoning text. |
| **AV** | Alpha Vantage LLM-scored news across 15 topic categories. |
| **EODHD** | EODHD alternative sentiment (currently 0% populated). |
| **MarketAux** | Entity-level sentiment, best for SGX tickers. |
| **FMP** | Aggregated social sentiment from Reddit + Twitter via FMP. |

#### Options Flow
Smart money positioning from options markets. **One of the strongest leading indicators.**

| Field | What It Means |
|-------|---------------|
| **P/C Ratio** | Put/Call ratio. >1.0 = more puts being bought (bearish positioning). <0.7 = bullish. Normal range: 0.7-1.0. |
| **IV Skew** | Implied volatility skew. Negative = puts are more expensive than calls (market is hedging downside). |
| **IV Percentile** | Where current implied volatility sits vs the last year. 90th = very high IV (fear/uncertainty). |
| **Unusual Options** | Flag when unusual sweep orders detected (large, aggressive, crossing the ask). Direction: bullish or bearish. |
| **Options Signal** | Combined options sentiment signal (-1 to +1). |
| **Dark Pool** | Dark pool volume — institutional block trades. High volume = institutional interest. |

#### Social & Retail
Retail investor sentiment and attention.

| Field | What It Means |
|-------|---------------|
| **Reddit Mentions** | ApeWisdom mention count across r/wallstreetbets, r/stocks, r/investing. |
| **Reddit Rank** | Rank by mention count. #1 = most discussed ticker on Reddit. |
| **Reddit Spike** | Flag when mentions spike >2σ above 30-day average. Spikes often precede moves. |
| **StockTwits Bullish %** | Self-tagged bullish/bearish from StockTwits users. >60% = retail bullish. |
| **X/Twitter** | Social score from X/Twitter (requires xAI API — not yet configured). |

#### Insider Activity
Corporate insider buying/selling — **historically one of the strongest mid-term signals**.

| Field | What It Means |
|-------|---------------|
| **Cluster Buy** | Flag when 3+ distinct insiders buy within a 30-day window. Academic research shows cluster buys predict 6-12 month outperformance. |
| **Buyers (30d)** | Number of distinct insider buyers in the last 30 days. |
| **Net (30d)** | Net dollar value: insider buys minus insider sells over 30 days. Negative = more selling (can be normal for executives exercising options). |

#### Signal Quality
How reliable is the composite signal?

| Field | What It Means |
|-------|---------------|
| **Source Agreement** | Standard deviation of source scores. Low (<0.15) = sources agree (reliable). High (>0.30) = sources disagree (less reliable). The trigger layer reduces confidence when agreement is low. |
| **Conviction Asymmetry** | Whether bullish or bearish evidence dominates. High positive = mostly bullish articles. High negative = mostly bearish. Near zero = balanced. |
| **Organic Score** | Composite excluding propagated/supply-chain signals. Only articles directly about THIS ticker. If organic differs from composite, the signal is partly borrowed from related stocks. |
| **Propagation Flag** | Whether this ticker's signal was partly inherited from a supply chain partner (e.g., TSMC news propagating to NVDA). |

#### Analyst Actions
Sell-side analyst activity.

| Field | What It Means |
|-------|---------------|
| **Action Detected** | Whether a named analyst firm issued an upgrade/downgrade/initiation in recent articles. |
| **Firm** | The specific analyst firm (e.g., Goldman Sachs, Morgan Stanley). |
| **Action Type** | upgrade / downgrade / initiate / reiterate. |
| **Consensus** | Aggregated consensus: strong_buy, buy, hold, sell, strong_sell. |

#### Events
Upcoming catalysts that may impact the stock.

| Field | What It Means |
|-------|---------------|
| **Forward Event** | Whether articles mention an upcoming catalyst (earnings, product launch, FDA decision, M&A). |
| **Event Type** | earnings / product_launch / regulatory / m_and_a / conference. |
| **Earnings In** | Days until next earnings report. The trigger layer flags tickers within 7 days of earnings as elevated uncertainty. |

#### Divergence
When sentiment and price action disagree — a contrarian indicator.

| Field | What It Means |
|-------|---------------|
| **Price Return 5d** | Stock's 5-day price return. |
| **Price Divergence** | Flag when sentiment direction contradicts price direction (e.g., positive sentiment but falling price). |
| **Direction** | bullish_on_falling (contrarian buy signal) or bearish_on_rising (contrarian sell signal). |

#### Google Trends
Search attention — often leads price moves by 1-3 days.

| Field | What It Means |
|-------|---------------|
| **Interest 7d** | Google search interest score (0-100) over the last 7 days. |
| **Interest 30d** | Google search interest score over the last 30 days. |
| **7d Change** | Percentage change in search interest vs prior week. |
| **Spike Flag** | Flag when search interest spikes >2σ above 30-day average. |

*Note: Google Trends data is currently 0% populated — needs sentimental_blogs fix.*

---

## Deep Analysis

The Deep Analysis tab shows **Gemini Pro narrative analyses** for flagged tickers. These are triggered when a ticker has:
- Unusual composite score (top/bottom movers)
- Price-sentiment divergence
- Unusual options activity
- High headline count (newsworthy event)

Each analysis contains:
- Full narrative with themes, risks, catalysts
- Contrarian view (what could go wrong with the consensus)
- Trigger reason (why Layer 2 analysis was activated)
- Composite score and regime at time of analysis

Approximately 10-20 tickers per crawl receive deep analysis.

---

## Moby Picks

Weekly analyst picks from Moby.co newsletter, parsed from markdown reports into DuckDB.

| Field | What It Means |
|-------|---------------|
| **Rating** | Overweight (buy) / Equal-weight (hold) / Underweight (sell) |
| **Price Target** | Moby's price target |
| **Upside %** | Expected upside to target |
| **Target Date** | When Moby expects the target to be reached |
| **Thesis** | Investment thesis summary |
| **Conclusion** | Moby's closing statement |

---

## Crawl Health

The status bar at the top of the Sentiment page shows:
- **Last crawl**: How long ago the most recent crawl completed
- **Tickers scored**: How many tickers were successfully processed
- **Articles**: Total articles fetched in the crawl
- **Failures**: Number of tickers where LLM scoring failed
- **Market regime**: VIX-based regime classification at crawl time

Color coding: Green (>95% success, 0 failures), Yellow (>85%), Red (<85%).

---

## Data Coverage (as of 2026-03-24)

| Signal Category | Coverage | Notes |
|----------------|----------|-------|
| Composite score | 90% | Primary signal — most tickers have data |
| LLM score | 89% | Gemini Flash article scoring |
| Options (PCR, IV skew) | 60-94% | Good coverage for US large/mid cap |
| ApeWisdom (Reddit) | 98-100% | Excellent — most tickers tracked |
| Insider activity | 52-70% | Good for US stocks, sparse for SGX |
| Analyst actions | 33% | Only when recent upgrade/downgrade detected |
| Conviction asymmetry | 36% | Requires sufficient article volume |
| Source agreement | 90% | Available whenever composite exists |
| Organic score | 90% | Available whenever composite exists |
| EODHD score | 0% | Crawler bug — not writing to DuckDB |
| Finnhub score | 0% | Crawler bug — not writing to DuckDB |
| StockTwits | 0% | Not writing to DuckDB |
| X/Twitter | 0% | xAI API not configured |
| Google Trends | 0% | Not writing to DuckDB |
| Dark pool | 0% | Not implemented |

---

## Related Documents

- [Sentiment DuckDB Integration Proposal](sentiment-duckdb-integration-proposal.md) — implementation phases, migration plan
- [Engine-SentimentPulse Gap Analysis](../docs/12-engine-sentimentpulse-gap-analysis.md) — original gap fixes
- [SentimentPulse Features & Functions](../../sentimental_blogs/docs/14-features-and-functions.md) — crawler module reference
- [Moby Extraction Prompt](moby-extraction-prompt.md) — Comet browser prompt for Moby data
