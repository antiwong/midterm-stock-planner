# Reddit Sentiment Integration Analysis

> [Back to Documentation Index](README.md) | [Sentiment Integration Plan](sentiment-integration.md)

**Date**: 2026-03-17
**Status**: Planned (Phase B) — waiting for EODHD sentiment regression results first

---

## Value Proposition

Reddit provides **retail crowd sentiment** — a fundamentally different signal from institutional news sources (Finnhub, EODHD, Alpha Vantage).

### What Reddit Gives Us

| Source | Signal Type | Latency | Coverage |
|--------|-----------|---------|----------|
| Finnhub/EODHD | Institutional news (earnings, analyst, filings) | Minutes-hours | Major tickers only |
| Alpha Vantage | News aggregation | Hours | Major tickers |
| **Reddit** | **Retail sentiment, hype detection, contrarian signals** | **Real-time** | **All tickers including small caps** |

### Unique Signals

1. **Early hype detection** — Reddit buzzes about stocks days/weeks before mainstream news (GME, AMC, TSLA were Reddit-first)
2. **Contrarian indicator** — Extreme Reddit bullishness often marks local tops; extreme bearishness can mark bottoms
3. **Coverage gap fill** — Smaller moby tickers (PODD, GRMN, TPR, BWA) get zero news from Finnhub/EODHD but may have Reddit discussion
4. **Volume/attention signal** — Mention count alone (ignoring sentiment) predicts volatility spikes

---

## The Noise Problem

Reddit is **extremely noisy**. Raw sentiment is nearly useless without heavy filtering.

| Noise Type | Example | Impact |
|-----------|---------|--------|
| Memes/jokes | "NVDA to the moon" | False positive sentiment |
| Bot/shill accounts | Coordinated pump posts | Inflated mention counts |
| Off-topic mentions | "I sold my AAPL to buy a car" | Irrelevant context |
| Sarcasm | "Great job INTC, another year of losses" | Inverted sentiment |
| Penny stock spam | Micro-cap pump-and-dumps | Pollutes signal |
| Stale discussions | Rehashing old news | No new information |

---

## Noise Filtering Strategy (4 Layers)

### Layer 1 — Source Filtering
- **Include**: r/wallstreetbets, r/stocks, r/investing, r/stockmarket (4 subs)
- **Exclude**: r/pennystocks, r/cryptocurrency, r/options (too noisy)
- Only posts with >5 upvotes (filters spam/bots)
- Only comments with >3 upvotes

### Layer 2 — Content Filtering
- Only count tickers from our watchlist (ignore unknown symbols)
- Require ticker mentioned in financial context (near words like "buy", "sell", "earnings", "price", "position")
- Minimum 20-character post length (filters meme-only posts)
- Deduplicate cross-posts across subreddits

### Layer 3 — Scoring
- Use **FinBERT** (not lexicon) — trained on financial text, handles context like "bearish" vs "bullish"
- Weight by upvote ratio: `score * sqrt(upvotes)` — crowd-validated opinions count more
- Separate **mention_count** from **sentiment_score** — both are features but measure different things
- Compute **sentiment_divergence**: Reddit sentiment minus news sentiment. When they diverge strongly, that's the strongest signal.

### Layer 4 — Temporal
- Use 1-day, 3-day, 7-day rolling windows (Reddit moves fast, shorter than news 14d)
- **Spike detection**: sudden 3x increase in mentions = something is happening
- **Decay weighting**: yesterday's posts count more than last week's

---

## Features to Generate

| Feature | Description | Expected Signal |
|---------|-------------|----------------|
| `reddit_mention_count_1d/3d/7d` | Number of times ticker discussed | Volatility predictor |
| `reddit_sentiment_mean_1d/3d/7d` | Average FinBERT score | Directional (weak) |
| `reddit_sentiment_divergence_7d` | Reddit minus news sentiment | Contrarian signal (strongest) |
| `reddit_mention_spike` | Current count / 30-day avg ratio | Event detection |
| `reddit_upvote_weighted_sentiment` | Sentiment x sqrt(upvotes) | Quality-filtered direction |

That's 5 feature types x 3 windows = **~11 Reddit features** added to the existing 39 + 12 news sentiment.

---

## Honest Assessment

| Aspect | Rating | Reasoning |
|--------|--------|-----------|
| Signal strength | **Low-Medium** | Academic research shows ~2-3% alpha from social sentiment, decaying over days |
| Noise level | **Very High** | Needs heavy filtering (4 layers) to be usable |
| Coverage improvement | **Medium** | Helps for tech/semi tickers; useless for precious metals, boring stocks |
| Implementation effort | **Medium** | PRAW library is easy; filtering pipeline is the real work |
| Risk of overfitting | **High** | Reddit sentiment is trendy — what works now may not work in 6 months |
| Maintenance burden | **Medium** | Reddit API changes, subreddit rule changes, bot waves |

### Comparison with Current Sources

Our EODHD daily sentiment already gives us pre-scored, clean, institutional-grade sentiment for all tickers. Reddit would add a **retail** dimension that's orthogonal but noisy.

---

## Implementation Plan

### Prerequisites (must complete first)
1. Wait for 30 days of EODHD sentiment data accumulation (~2026-04-16)
2. Run regression test with `use_sentiment=true` on EODHD data
3. **If EODHD shows positive Sharpe impact** → proceed with Reddit (it's a different signal)
4. **If EODHD shows no impact** → Reddit unlikely to help either (skip)

### Phase 1 — Mention Count Only (Lowest Noise)
- Install PRAW (`pip install praw`)
- Build `src/sentiment/sources/reddit.py`
- Scrape daily mention counts from 4 subreddits
- No sentiment scoring needed — just volume
- Feature: `reddit_mention_count_1d/3d/7d` + `reddit_mention_spike`
- **Why first**: Most robust signal, least noise, cheapest to implement

### Phase 2 — Sentiment Scoring (If Phase 1 Shows Signal)
- Score posts with FinBERT (not lexicon — too noisy for Reddit)
- Apply upvote weighting
- Features: `reddit_sentiment_mean`, `reddit_upvote_weighted_sentiment`

### Phase 3 — Divergence Signal (If Phase 2 Shows Signal)
- Compute Reddit vs EODHD/news sentiment divergence
- Feature: `reddit_sentiment_divergence_7d`
- This is the highest-value but most complex feature

### Reddit API Setup
```bash
# 1. Create Reddit app at https://www.reddit.com/prefs/apps
# 2. Choose "script" type
# 3. Add credentials to .env:
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_secret
REDDIT_USER_AGENT=stock-planner/1.0

# 4. Install PRAW
pip install praw
```

---

## References

- [Sentiment Integration Plan](sentiment-integration.md) — overall phased approach
- [Sentiment Data Audit](sentiment-data-audit.md) — current data quality assessment
- Academic: Bollen et al. (2011) "Twitter mood predicts the stock market" — 87.6% accuracy on DJIA direction
- Academic: Chen et al. (2014) "Wisdom of Crowds: The Value of Stock Opinions Transmitted Through Social Media" — SeekingAlpha comments predict returns
- r/wallstreetbets — ~14M members, primary retail sentiment source
