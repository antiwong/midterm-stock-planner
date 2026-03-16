# Sentiment Data Audit

> [Back to Documentation Index](README.md) | [Sentiment Integration Plan](sentiment-integration.md)

**Date**: 2026-03-17
**Status**: Data quality insufficient for regression testing — daily accumulation started via cron

---

## Data Inventory

### Sources Used

| Source | API Key | Tier | Rate Limit | What It Provides |
|--------|---------|------|------------|------------------|
| **Finnhub** | Set | Free | 60 calls/min | News articles, insider transactions, analyst recommendations, earnings surprises |
| **Alpha Vantage** | Set | Free | 5 calls/min | Pre-scored news sentiment (AV proprietary scoring) |
| **NewsAPI** | Set | Free | 100 requests/day | News headlines from 80,000+ sources |
| **OpenAI** | Set | Paid | — | LLM scoring (not yet used for sentiment) |
| Reddit/X | Not set | — | — | Not implemented |

### Data Files

| File | Rows | Tickers | Date Range | Source |
|------|------|---------|------------|--------|
| `data/sentiment/news.csv` | 2,026 | 13 | 2026-03-08 to 2026-03-16 | Finnhub + Alpha Vantage |
| `data/sentiment/insider_transactions.csv` | 3,057 | 7 | Various | Finnhub |
| `data/sentiment/analyst_recommendations.csv` | 28 | 7 | Quarterly | Finnhub |
| `data/sentiment/earnings_surprises.csv` | 28 | 7 | Quarterly | Finnhub |

### Coverage Matrix (tech_giants)

| Ticker | News | Insider | Analyst | Earnings | News Source | Days of Data |
|--------|------|---------|---------|----------|-------------|--------------|
| AAPL | 248 | 118 | 4 | 4 | Finnhub | 8 |
| MSFT | 250 | 155 | 4 | 4 | Finnhub | 5 |
| GOOGL | 247 | 708 | 4 | 4 | Finnhub | 5 |
| AMZN | 249 | 310 | 4 | 4 | Finnhub | 5 |
| META | 244 | 867 | 4 | 4 | Finnhub | 4 |
| NVDA | 250 | 705 | 4 | 4 | Finnhub | 1 |
| TSLA | 241 | 194 | 4 | 4 | Finnhub | 6 |
| AMD | 49 | 0 | 0 | 0 | Alpha Vantage | 2 |
| INTC | 49 | 0 | 0 | 0 | Alpha Vantage | 2 |
| ORCL | 50 | 0 | 0 | 0 | Alpha Vantage | 3 |
| CRM | 50 | 0 | 0 | 0 | Alpha Vantage | 2 |
| ADBE | 50 | 0 | 0 | 0 | Alpha Vantage | 3 |
| NFLX | 49 | 0 | 0 | 0 | Alpha Vantage | 3 |

---

## Quality Issues

### Critical

1. **Insufficient date range** — News data covers 1-8 days, not the 180 days requested. Finnhub free tier returns recent articles only (~250 max regardless of date range). Alpha Vantage free tier returns 50 articles from last few days.

2. **No historical depth** — The LightGBM model trains on walk-forward windows spanning months/years. Sentiment features computed from only a few days of news will be almost entirely zeros (fillna=0.0) for most of the training period.

3. **Two-tier coverage** — 7 tickers (FAANG+TSLA) have full multi-source data. 6 tickers (AMD, INTC, ORCL, CRM, ADBE, NFLX) have news-only from Alpha Vantage with no insider/analyst/earnings data.

### High

4. **Source bias** — 66% of articles from Yahoo Finance. Single-source dominance means sentiment scores reflect Yahoo's editorial choices, not true market sentiment.

5. ~~No sentiment scoring~~ **RESOLVED** (2026-03-17) — All 2,026 articles scored with lexicon model. Columns added: `sentiment_score` (headline), `summary_sentiment`, `combined_sentiment` (60% headline + 40% summary). Distribution: 45% positive, 35% neutral, 20% negative.

### Medium

6. **Missing summaries** — 27 articles have no summary text (headline only). Lexicon scoring on short headlines is less accurate.

7. **No deduplication across sources** — Same story may appear from multiple sources (Yahoo, Benzinga, SeekingAlpha) with slightly different headlines, inflating article count.

---

## What's Needed Before Regression Testing

### Minimum Viable Sentiment Data

| Requirement | Current | Target | Gap |
|-------------|---------|--------|-----|
| Date range | 1-8 days | 180+ days | Critical — need daily accumulation |
| All tickers covered | 7 full, 6 partial | 13 full | Need paid tier or more sources |
| Insider data | 7 tickers | 13 tickers | Finnhub free tier limitation |
| Analyst data | 7 tickers | 13 tickers | Same |
| Pre-scored | **Yes (done)** | Yes | Lexicon model scored 2,026 articles |
| Deduplicated | No | Yes | Remove cross-source duplicates |

### Options to Build Historical Depth

| Option | Cost | Coverage | Historical Depth | Effort |
|--------|------|----------|-----------------|--------|
| **Daily cron accumulation** | Free | Current sources | Builds over weeks/months | **Active** — cron at 6:00 PM ET |
| **Finnhub paid tier** | $50/mo | Full API access | Up to 1 year | Low — same code |
| **NewsAPI paid tier** | $449/mo | 80,000+ sources | 5+ years | Low — same code |
| **Reddit (PRAW)** | Free | Reddit only | Up to 1 year (pushshift) | Medium — new source |
| **Polygon.io** | $79/mo | Comprehensive | 5+ years | Medium — new integration |
| **Synthetic backfill** | Free | Existing sources | Approximation only | Low but questionable |

### Recommended Path

1. **Start daily sentiment accumulation now** — Add Finnhub download to the daily cron job. Over 30 days, we'll have enough data to start testing.

2. **Score existing articles immediately** — Run lexicon model on all 2,026 articles to generate `sentiment_score` column.

3. **Evaluate after 30 days** — With 30 days of daily-accumulated data, run regression test to see if sentiment has signal.

4. **If positive** — Invest in paid tier (Finnhub $50/mo) or Reddit integration for historical backfill.

5. **If negative** — Sentiment may not add value for our cross-sectional ranking model (similar to how RSI, momentum, and OBV hurt Sharpe in regression tests).

---

## Data Source Documentation

### Finnhub (Primary)
- **Endpoint**: `/company-news` — news articles with headline, summary, URL, source
- **Endpoint**: `/stock/insider-transactions` — insider buys/sells with amounts
- **Endpoint**: `/stock/recommendation` — analyst buy/hold/sell consensus
- **Endpoint**: `/stock/earnings` — actual vs estimate EPS
- **Free tier**: 60 calls/min, recent data only (~1 week of news)
- **Paid tier** ($50/mo): Higher limits, extended history
- **Script**: `scripts/download_sentiment.py`

### Alpha Vantage (Gap Fill)
- **Endpoint**: News Sentiment API — pre-scored articles with relevance
- **Free tier**: 5 calls/min, 25/day, last few days only
- **Scoring**: Proprietary sentiment score (-1.0 to +1.0), not stored in our CSV
- **Module**: `src/sentiment/sources/alpha_vantage.py`

### NewsAPI (Supplementary)
- **Endpoint**: Everything API — headlines from 80,000+ sources
- **Free tier**: 100 requests/day, last 30 days
- **Scoring**: None (headlines only, need lexicon/FinBERT)
- **Module**: `src/sentiment/sources/newsapi.py`

### Not Yet Integrated
- **Reddit** (PRAW): r/wallstreetbets, r/stocks — high volume, noisy
- **Polygon.io**: Comprehensive news + reference data
- **Twitter/X**: Real-time sentiment, API access restricted

---

## See Also

- [Sentiment Integration Plan](sentiment-integration.md) — phased approach (A/B/C/D)
- [Sentiment Module](../src/sentiment/) — code reference
- [Feature Engineering](data-engineering.md) — how features feed into model
- Config: `config/config.yaml` → `features.use_sentiment`, `sentiment.*`
