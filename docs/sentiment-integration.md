# Sentiment Integration Plan

> [Back to Documentation Index](README.md)

**Date**: 2026-03-17 (updated)
**Status**: Phase A complete — EODHD integrated as primary sentiment source

---

## Background

The sentiment analysis infrastructure is fully built but not wired into the daily ML pipeline. This document captures the decision process and integration plan.

## Current State

### What's Built

| Component | Status | Details |
|-----------|--------|---------|
| Sentiment models | Ready | Lexicon (fast), FinBERT (accurate), LLM (OpenAI/Gemini) |
| Data sources | Ready | **EODHD (primary)**, Alpha Vantage, NewsAPI, Finnhub (news + insider + analyst + earnings), RSS feeds |
| Feature pipeline | Ready | `prepare_sentiment_from_news()` → rolling aggregation → merge via (date, ticker) |
| Config support | Ready | `use_sentiment: false` — flip to enable |
| API keys | Set | **EODHD**, Alpha Vantage, NewsAPI, Finnhub, OpenAI |
| Reddit/X | Not built | Config stub exists (`sentiment_source: "social"`) |

### Coverage Problem (as of 2026-03-16)

Live test on 14 Moby tickers with 7-day lookback:

| Source | Tickers with data | Missing |
|--------|------------------|---------|
| Alpha Vantage | 8/14 (57%) | ORCL, AMD, GRMN, EMR, WMT, SWKS |
| NewsAPI | 6/14 (43%) | PODD, GRMN, DXC, EMR, ROK, WMT, SWKS, TPR |
| Finnhub | TBD (downloading) | Expected best coverage |

**Key finding**: Only major tickers (NVDA, META, INTC) get decent coverage from both sources. Smaller names return nothing. This means sentiment features will be mostly zeros for half the universe.

### Live Sentiment Scores (2026-03-16)

| Ticker | Alpha Vantage | NewsAPI | Combined | Signal |
|--------|-------------|---------|----------|--------|
| NVDA | +0.250 | +0.200 | +0.230 | STRONG BUY |
| INTC | +0.103 | +0.333 | +0.195 | BUY |
| ADBE | -0.043 | +0.500 | +0.174 | BUY |
| ORCL | N/A | +0.375 | +0.150 | BUY |
| META | +0.185 | +0.033 | +0.124 | BUY |
| PODD | -0.319 | N/A | -0.192 | SELL |
| DXC | -0.164 | N/A | -0.098 | SELL |

---

## Integration Decision: Option A (Wire Existing)

### Why Option A

Three options were evaluated:

| Option | Description | Effort | Risk |
|--------|------------|--------|------|
| **A** | Wire existing sources into ML pipeline | Low (1-2h) | Sparse data may hurt model |
| B | Add Reddit first, then wire in | Medium (1 day) | Reddit noise, API setup |
| C | Use LLM scoring (GPT) | Medium | API costs, slower |

**Decision**: Start with A. The regression test will definitively show whether sentiment helps or hurts Sharpe ratio. If it hurts (like RSI and momentum did), we skip it and avoid investing in Reddit/LLM. If it helps, we invest in better sources.

### Implementation Steps

1. **Download sentiment history** (Finnhub, 180 days, tech_giants) → `data/sentiment/`
2. **Enable in config**: `use_sentiment: true`
3. **Wire into `_load_data()`** in paper trading pipeline
4. **Run regression test** with sentiment to measure impact
5. **Compare**: Sharpe with/without sentiment features

### Sentiment Features Generated

For each (ticker, date) with lookback windows of 1, 7, 14 days:

| Feature | Description |
|---------|-------------|
| `sentiment_mean_{N}d` | Average sentiment score over N-day window |
| `sentiment_std_{N}d` | Sentiment volatility (disagreement) |
| `sentiment_count_{N}d` | Article volume (more articles = more attention) |
| `sentiment_trend_{N}d` | Sentiment momentum (improving or deteriorating) |

That's 4 features x 3 windows = **12 sentiment features** added to the existing 39.

### Risk Mitigation

- **Sparse data**: `fillna_value: 0.0` — missing sentiment = neutral, won't bias the model
- **Look-ahead prevention**: `filter_news_to_asof()` ensures no future articles leak into training
- **Regression gating**: Only keep sentiment if regression test shows positive Sharpe impact

---

## Daily Automation (Active as of 2026-03-17)

```
# Cron schedule (weekdays):
5:30 PM ET  →  paper_trading.py run (signals + execution)
6:00 PM ET  →  download_sentiment.py (Finnhub news/insider/analyst/earnings)
             →  score_sentiment.py (lexicon model scoring)
```

Logs: `logs/paper_trading.log`, `logs/sentiment_download.log`

### Scoring Status
- 2,026 articles scored with lexicon model (2026-03-17)
- Combined sentiment: 60% headline weight + 40% summary weight
- Distribution: 45% positive, 35% neutral, 20% negative
- Per-ticker scores range from +0.030 (ADBE, neutral) to +0.365 (NVDA, bullish)

### Data Accumulation Timeline
- **Day 1** (2026-03-17): 2,026 articles, 1-8 days coverage
- **Day 30** (~2026-04-16): Target 30 days of daily data → run regression test
- **Day 90** (~2026-06-15): Sufficient depth for walk-forward sentiment features

---

## EODHD — Primary Sentiment Source (Added 2026-03-17)

EODHD provides the best sentiment data quality of all sources on the free plan.

### What It Provides

| Endpoint | Data | Cost | Quality |
|----------|------|------|---------|
| `/sentiments` | Daily aggregated score (0-1) + article count per ticker | 1 call/ticker | Excellent — pre-computed, normalized |
| `/news` | Articles with polarity + pos/neg/neu breakdown | 5 calls each | Good — pre-scored per article |
| `/eod/{ticker}` | OHLCV prices | 1 call | Standard |
| `/fundamentals` | PE, PB, EPS, balance sheets | **Blocked (403)** | Needs $59.99/mo |

### Quality Comparison

| Metric | Finnhub | Alpha Vantage | **EODHD** |
|--------|---------|---------------|-----------|
| Tickers with daily sentiment | 0 | 0 | **8/8 (100%)** |
| Days per API call | 1-8 | 2-3 | **16+** |
| Pre-scored articles | No | Yes (proprietary) | **Yes (polarity + breakdown)** |
| Daily aggregated scores | No | No | **Yes (normalized 0-1)** |
| Article count tracking | No | No | **Yes (32-182/day)** |
| Free tier daily calls | 60 | 5 | 20 |

### Initial Download Results (2026-03-17)

8 tickers, 16 days of daily sentiment:

| Ticker | Avg Score | Sentiment | Avg Articles/Day |
|--------|-----------|-----------|-----------------|
| AMD | 0.815 | Bullish | 32 |
| MSFT | 0.815 | Bullish | 55 |
| INTC | 0.795 | Bullish | 87 |
| NVDA | 0.754 | Bullish | 182 |
| META | 0.745 | Bullish | 46 |
| AAPL | 0.714 | Bullish | 50 |
| TSLA | 0.697 | Bullish | 45 |
| ORCL | 0.693 | Bullish | 34 |

### Pricing (if upgrading)

| Plan | Price | What It Adds |
|------|-------|-------------|
| Free (current) | $0 | EOD prices, news (4 req/day), daily sentiment |
| Calendar & News | $19.99/mo | Unlimited news, economic calendar |
| Fundamentals | $59.99/mo | PE, PB, EPS — but regression shows zero Sharpe impact |
| All-in-One | $79.99/mo | Everything above + real-time |

**Recommendation**: Stay on free plan. Daily sentiment accumulation via cron is sufficient. Fundamentals not worth $59.99/mo since regression tests show valuation features have zero impact.

### Files

- Source: `src/sentiment/sources/eodhd.py`
- Daily sentiment: `data/sentiment/eodhd_daily_sentiment.csv`
- News articles: `data/sentiment/eodhd_news.csv`

---

## Moby Email Integration (Planned)

**Source**: `antiwongmoby@gmail.com` — Moby analytics newsletter emails
**Status**: Not yet connected. Gmail MCP is linked to main account only.

**Integration options**:
1. Connect antiwongmoby@gmail.com to Gmail MCP
2. Forward Moby emails to the connected account
3. Build direct Gmail API integration for the antiwongmoby account

**What Moby emails contain**:
- Portfolio tier changes (platinum/gold/silver allocations)
- Stock recommendations with target prices and rationale
- Sector rotation signals
- Market commentary with directional sentiment

**Parsing plan**:
- Extract ticker mentions + recommendation type (buy/sell/hold)
- Map to `sentiment_score` (-1 to +1) based on recommendation strength
- Tier changes → weight adjustments in moby_picks watchlist

See beads issue `midterm-stock-planner-81n` for tracking.

---

## Future Phases

### Phase B: Reddit/Social Media
- Install PRAW (Reddit API wrapper)
- Build `RedditSource` class in `src/sentiment/sources/`
- Scrape r/wallstreetbets, r/stocks, r/investing
- Extract: mention count, comment sentiment, upvote ratio
- Better coverage for tech/semi tickers than news APIs
- **Prerequisite**: Phase A regression shows sentiment has signal

### Phase C: LLM-Enhanced Scoring
- Use OpenAI GPT-4 to score headlines with financial context
- Better than lexicon for nuance (e.g., "NVDA beats earnings but guides lower" = bearish despite "beats")
- Hybrid approach: lexicon for bulk processing, LLM for top-N picks only
- **Prerequisite**: Phase A/B shows sentiment has signal, justify API cost

### Phase D: Real-Time Sentiment
- Stream news via Finnhub WebSocket (paid tier)
- Intraday sentiment updates during market hours
- Alert system when sentiment shifts sharply
- **Prerequisite**: Paper trading validates sentiment improves live performance

---

## References

- Config: `config/config.yaml` lines 88-120
- Sentiment module: `src/sentiment/`
- Download script: `scripts/download_sentiment.py`
- Feature engineering: `src/features/engineering.py` → `prepare_sentiment_from_news()`
- Inspired by: [daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis) multi-source sentiment approach
