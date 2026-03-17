# Stock Market Data Providers Guide

> [← Back to Documentation Index](README.md)
> Last updated: March 2026
>
> Comprehensive reference for programmatic stock data retrieval services.
> Covers pricing, API quality, Python integration, and recommendations for
> mid-term ML-based stock analysis (SLV/precious metals, AMD/semiconductors).

---

## Quick Recommendation Summary

| Category | Top Pick (Paid) | Top Pick (Free/Cheap) | Why |
|---|---|---|---|
| **Price Data (OHLCV)** | Polygon.io / Massive ($29+/mo) | Alpaca Markets (free) | Polygon: tick-level depth. Alpaca: 7 yr intraday free with account |
| **Sentiment & News** | Finnhub ($50/mo) | Finnhub (free tier) | 60 req/min free, analyst recs, social sentiment, news |
| **Fundamentals** | FMP ($19/mo) | FMP (free, 250 calls/day) | Cleanest API, 30+ yr history, earnings + estimates |
| **Macro / Economic** | FRED (free) | FRED (free) | 800k+ series, no cost, excellent Python library |
| **Alternative Data** | Unusual Whales ($250/mo) | Quiver Quantitative ($10/mo) | Options flow vs. congressional/lobbying data |

**Recommended starter stack for this project:** Alpaca (prices) + Finnhub (sentiment/news) + FMP (fundamentals) + FRED (macro) = ~$70/mo total or $0 on free tiers.

---

## 1. Price Data Providers

### 1.1 Alpaca Markets

| Field | Details |
|---|---|
| **URL** | https://alpaca.markets/data |
| **Data Provided** | US stocks OHLCV, trades, quotes, snapshots, crypto |
| **Free Tier** | IEX-sourced data, 200 req/min, 7+ years of 1m/5m/15m/1h/daily bars |
| **Paid Tier** | $9/mo for Nasdaq SIP (full market data), unlimited API calls |
| **API Quality** | REST + WebSocket. Excellent docs. OpenAPI spec. |
| **Data Resolution** | 1-min, 5-min, 15-min, 1-hour, daily bars; trades & quotes |
| **History Depth** | 7+ years intraday, 20+ years daily |
| **Rate Limits** | Free: 200 req/min. Paid: unlimited |
| **Python Package** | `alpaca-py` (official), `alpaca-trade-api` (legacy) |
| **Ease of Integration** | 5/5 - Excellent Python SDK, pandas-friendly |
| **Project Fit** | Excellent for SLV (ETF) and AMD. Free tier is sufficient for backtesting. Best free intraday data source available. |

**Notes:** Requires a (free) Alpaca brokerage account. No trading required. The free IEX data feed is ~2% of the consolidated tape but OHLCV bars are computed from all exchanges. For historical bars, free and paid tiers return the same data.

---

### 1.2 Polygon.io (now Massive)

| Field | Details |
|---|---|
| **URL** | https://polygon.io (redirects to https://massive.com) |
| **Data Provided** | US stocks, options, forex, crypto - OHLCV, trades, quotes, order book |
| **Free Tier** | 5 req/min, limited endpoints, delayed data |
| **Paid Tiers** | Stocks Basic: $29/mo (unlimited delayed). Stocks Developer: $79/mo. Stocks Advanced: $199/mo (real-time, unlimited). Business plans from $499/mo. |
| **API Quality** | REST + WebSocket + Kafka. JSON/CSV output. Excellent docs. |
| **Data Resolution** | Tick-level, 1-sec, 1-min through daily. Full order book on higher tiers. |
| **History Depth** | 20+ years daily, 7+ years intraday minute bars, tick data varies |
| **Rate Limits** | Free: 5/min. Paid: unlimited on most plans |
| **Python Package** | `polygon` (official), `polygon-api-client` |
| **Ease of Integration** | 4/5 - Good SDK but requires handling pagination for large queries |
| **Project Fit** | Excellent if you need tick-level or sub-minute data for feature engineering. The $29/mo Basic plan is a strong upgrade over yfinance. Covers SLV and AMD. |

**Notes:** Rebranded to Massive in late 2025. Existing polygon.io endpoints and API keys continue to work. Flat-file downloads available for bulk historical data.

---

### 1.3 Alpha Vantage

| Field | Details |
|---|---|
| **URL** | https://www.alphavantage.co |
| **Data Provided** | US/global stocks, forex, crypto, commodities, economic indicators, technical indicators, news sentiment |
| **Free Tier** | 25 req/day, 5 req/min. Daily data only (adjusted/unadjusted). |
| **Paid Tiers** | Tier 1: $49.99/mo (75 req/min). Tier 2: $99.99/mo (150 req/min). Tier 3: $149.99/mo (300 req/min). Tier 4: $199.99/mo (600 req/min). Tier 5: $249.99/mo (1,200 req/min). Annual plans save ~2 months. |
| **API Quality** | REST only. JSON/CSV output. No WebSocket. |
| **Data Resolution** | 1-min, 5-min, 15-min, 30-min, 60-min, daily, weekly, monthly |
| **History Depth** | 20+ years daily (premium only for `outputsize=full`). 1-2 months intraday on free tier. |
| **Rate Limits** | Free: 25/day + 5/min. Paid: no daily limit, per-min varies by tier |
| **Python Package** | `alpha_vantage` (community) |
| **Ease of Integration** | 3/5 - Simple REST but slow due to rate limits on free tier. The built-in news sentiment endpoint is a nice bonus. |
| **Project Fit** | Decent all-rounder but expensive for what you get vs. Alpaca/Polygon. The news sentiment API is unique and useful for ML features. |

**Notes:** The free tier is very restrictive (25 calls/day). Premium-only features include full historical data and real-time prices. Better as a supplement (for sentiment/technical indicators) than a primary price source.

---

### 1.4 Tiingo

| Field | Details |
|---|---|
| **URL** | https://www.tiingo.com |
| **Data Provided** | US stocks, ETFs, mutual funds, ADRs, Chinese equities, crypto, forex, fundamentals, news |
| **Free Tier** | 50 symbols/hour, 500 req/hour. 30+ years daily history. 5 years fundamental data. |
| **Paid Tiers** | Power: $10/mo (5,000 req/hr). Commercial: $50/mo (20,000 req/hr). Institutional pricing available. |
| **API Quality** | REST + WebSocket (IEX real-time). JSON output. Clean API design. |
| **Data Resolution** | Daily, intraday (5-min on paid plans), real-time via WebSocket |
| **History Depth** | 50+ years daily for some tickers, 65,000+ symbols |
| **Rate Limits** | Free: 500 req/hr, 50 symbols/hr. Power: 5,000 req/hr. |
| **Python Package** | No official SDK; use `requests` or `pandas_datareader` (has Tiingo support) |
| **Ease of Integration** | 4/5 - Clean REST API, works well with pandas_datareader |
| **Project Fit** | Excellent cost-effective option for daily data. The free tier is generous enough for a small portfolio. Good SLV/AMD coverage. |

**Notes:** One of the best value-for-money providers. The free tier's 30+ year daily history is very competitive. Fundamentals data requires paid tier for full coverage.

---

### 1.5 EOD Historical Data (EODHD)

| Field | Details |
|---|---|
| **URL** | https://eodhd.com |
| **Data Provided** | Global stocks (70+ exchanges), ETFs, forex, crypto, fundamentals, macro |
| **Free Tier** | 20 req/day. Limited to US market. |
| **Paid Tiers** | All World: $19.99/mo. All World Extended (+ intraday): $29.99/mo. Fundamentals: $59.99/mo. All-in-One: $99.99/mo ($83.33/mo annual). |
| **API Quality** | REST only. JSON/CSV output. Good documentation with Python examples. |
| **Data Resolution** | 1-min, 5-min, 1-hour, daily |
| **History Depth** | 30+ years daily. Intraday varies by exchange. |
| **Rate Limits** | Free: 20/day. Paid: 100,000/day. |
| **Python Package** | `eodhd` (official) |
| **Ease of Integration** | 4/5 - Clean API, good Python examples in docs |
| **Project Fit** | Good all-rounder. The $29.99/mo Extended plan covers price + intraday. You'd need the $99.99 plan for fundamentals too. Slightly more expensive than Alpaca + FMP combo. |

---

### 1.6 Nasdaq Data Link (formerly Quandl)

| Field | Details |
|---|---|
| **URL** | https://data.nasdaq.com |
| **Data Provided** | Curated datasets: commodities, futures, economic data, alternative data. Less useful for raw stock prices now. |
| **Free Tier** | Some free datasets (FRED mirror, Wiki prices - discontinued). 300 req/10sec, 2,000/10min. |
| **Paid Tiers** | Dataset-dependent. Premium datasets $500+/mo (institutional pricing). |
| **API Quality** | REST. JSON/CSV. `nasdaqdatalink` Python package. |
| **Data Resolution** | Mostly daily. Some datasets have intraday. |
| **History Depth** | Dataset-dependent, often decades |
| **Rate Limits** | Free: 300/10sec. Premium: higher. |
| **Python Package** | `nasdaqdatalink` (official, successor to `quandl`) |
| **Ease of Integration** | 3/5 - API is fine but discovering the right dataset codes is confusing |
| **Project Fit** | Less relevant for stock prices post-Quandl. Useful for commodities data (gold/silver futures for SLV analysis). |

---

### 1.7 Interactive Brokers API

| Field | Details |
|---|---|
| **URL** | https://www.interactivebrokers.com/en/trading/ib-api.php |
| **Data Provided** | Everything traded on IBKR: stocks, options, futures, forex, bonds, crypto |
| **Free Tier** | Free with funded IBKR account ($500+ minimum). Some exchange data fees apply ($1-15/mo per exchange). |
| **Paid Tiers** | N/A - included with brokerage account. Exchange data subscriptions $1-15/mo each. |
| **API Quality** | Socket-based (TWS/Gateway). REST via Client Portal API. Complex but powerful. |
| **Data Resolution** | 1-sec, 5-sec, 1-min through monthly. Real-time streaming. |
| **History Depth** | Varies: ~1 year for seconds, ~2 years for minutes, 10+ years daily |
| **Rate Limits** | 6 identical requests/2sec. Pacing violations for repeated requests. |
| **Python Package** | `ibapi` (official TWS API), `ib_insync` (popular async wrapper) |
| **Ease of Integration** | 2/5 - Powerful but complex. Requires running TWS or IB Gateway. The async architecture has a learning curve. New synchronous wrapper (Oct 2025) helps. |
| **Project Fit** | Best if you already trade with IBKR. Not worth setting up just for data. Good for live trading integration later. |

---

### 1.8 Charles Schwab API (formerly TD Ameritrade)

| Field | Details |
|---|---|
| **URL** | https://developer.schwab.com |
| **Data Provided** | US stocks, ETFs, options, quotes, price history |
| **Free Tier** | Free with Schwab brokerage account |
| **Paid Tiers** | N/A - included with account |
| **API Quality** | REST + Streaming. OAuth2 auth (tokens expire every 7 days). |
| **Data Resolution** | 1-min, 5-min, 15-min, 30-min, daily, weekly, monthly |
| **History Depth** | 1 year intraday, 20+ years daily |
| **Rate Limits** | 120 req/min |
| **Python Package** | `schwab-py` (community, requires Python 3.10+) |
| **Ease of Integration** | 2/5 - OAuth token refresh every 7 days is painful. Migration from TDA was rocky. |
| **Project Fit** | Only if you already have a Schwab account. Token management is annoying for automated pipelines. |

---

### 1.9 Yahoo Finance (yfinance) - Current Provider

| Field | Details |
|---|---|
| **URL** | https://github.com/ranaroussi/yfinance |
| **Data Provided** | US/global stocks, ETFs, crypto, options, basic fundamentals |
| **Free Tier** | Free (unofficial scraper) |
| **Paid Tiers** | N/A |
| **API Quality** | Python library only. No official API. Scrapes Yahoo Finance. |
| **Data Resolution** | 1-min (7 days), 5-min (60 days), 1-hour (730 days), daily (max history) |
| **History Depth** | Full history for daily. Limited intraday (see above). |
| **Rate Limits** | Unofficial, aggressive use gets IP blocked. ~2,000 req/hr practical limit. |
| **Python Package** | `yfinance` |
| **Ease of Integration** | 4/5 for basic use, but 1/5 for reliability |
| **Project Fit** | Currently used by this project. Works for daily data but unreliable for production. Yahoo frequently changes their site, breaking yfinance. Major breakage occurred Feb 2025. Should be replaced or supplemented. |

**Known Issues (2025-2026):**
- Frequent breakage when Yahoo changes their site layout or API
- IP rate-limiting and blocking with heavy use
- No guaranteed data quality or SLA
- Feb 2025: major API change broke most yfinance versions
- Not suitable for automated daily pipelines

---

### 1.10 Databento

| Field | Details |
|---|---|
| **URL** | https://databento.com |
| **Data Provided** | US equities (all 15 exchanges + 30 ATSes), futures, options. Full order book, trades, OHLCV. |
| **Free Tier** | $125 free credit on signup |
| **Paid Tiers** | Standard: $199/mo (7yr OHLCV, 12mo L1 history, 1mo L2/L3). Professional: $499/mo. Enterprise: custom. As of Jan 2025, all plans include unlimited live data. |
| **API Quality** | REST + streaming. Protobuf and JSON. Nanosecond timestamps. 6.1us normalization latency. 99.99% uptime SLA. |
| **Data Resolution** | Tick-level (trade-by-trade), 1-sec, 1-min OHLCV, full MBO/MBP order book |
| **History Depth** | 7+ years OHLCV. 12 months L1. Expanding. |
| **Rate Limits** | Generous - designed for institutional workloads |
| **Python Package** | `databento` (official) |
| **Ease of Integration** | 4/5 - Excellent SDK, but overkill for daily/weekly analysis |
| **Project Fit** | Overkill for mid-term analysis. Worth it only if you need tick-level microstructure features. The $199/mo price is steep for this project's needs. |

---

## 2. Sentiment & News Providers

### 2.1 Finnhub

| Field | Details |
|---|---|
| **URL** | https://finnhub.io |
| **Data Provided** | Company news, market news, analyst recommendations, social sentiment, earnings surprises, insider trading, congressional trading, FDA calendars, ESG scores |
| **Free Tier** | 60 req/min. Access to: US stock quotes, company news, basic fundamentals, SEC filings, WebSocket (50 symbols) |
| **Paid Tiers** | Market Data Basic: $49.99/mo. Standard: $129.99/mo. Professional: $199.99/mo. Fundamental Data: $50/mo. Estimates: $75/mo. A la carte pricing by data category. |
| **API Quality** | REST + WebSocket. Clean JSON. Well-documented. |
| **Python Package** | `finnhub-python` (official) |
| **Ease of Integration** | 5/5 - One of the best-designed financial APIs |
| **Project Fit** | Excellent. The free tier alone gives you analyst recommendations, news sentiment, insider trading, and earnings calendars. Perfect for ML feature engineering. |

**Key endpoints for this project:**
- `/stock/recommendation` - analyst consensus (buy/hold/sell)
- `/company-news` - news articles with sentiment
- `/stock/insider-transactions` - insider buying/selling
- `/calendar/earnings` - upcoming earnings dates
- `/stock/social-sentiment` - Reddit/Twitter buzz

---

### 2.2 Alpha Vantage News Sentiment

| Field | Details |
|---|---|
| **URL** | https://www.alphavantage.co/documentation/#news-sentiment |
| **Data Provided** | News articles with AI-generated sentiment scores, relevance scores, ticker-specific sentiment |
| **Free Tier** | Included in free tier (25 req/day limit) |
| **Paid Tiers** | Same as price data tiers ($49.99-$249.99/mo) |
| **Python Package** | `alpha_vantage` |
| **Ease of Integration** | 3/5 - Simple endpoint but rate-limited |
| **Project Fit** | Good supplement. The ticker-level sentiment scores (bullish/bearish/neutral with confidence) are directly usable as ML features. |

---

### 2.3 NewsAPI

| Field | Details |
|---|---|
| **URL** | https://newsapi.org |
| **Data Provided** | General news articles from 150,000+ sources. Not finance-specific. |
| **Free Tier** | 100 req/day (development only, not for production) |
| **Paid Tiers** | Business: $449/mo. Enterprise: custom. |
| **Python Package** | `newsapi-python` |
| **Ease of Integration** | 4/5 - Simple API, but requires your own NLP for sentiment |
| **Project Fit** | Limited. General news, not financial. You'd need to filter and run your own sentiment analysis. Finnhub is better for this use case. |

---

### 2.4 Benzinga

| Field | Details |
|---|---|
| **URL** | https://www.benzinga.com/apis |
| **Data Provided** | Real-time financial news, analyst ratings, earnings, M&A, SEC filings, "Why is it Moving" sentiment |
| **Free Tier** | 14-day trial |
| **Paid Tiers** | API licensing starts ~$200/mo. Benzinga Pro: Basic $37/mo, Essential $199/mo (annual billing). |
| **API Quality** | REST + WebSocket + Webhooks. OpenAPI documented. |
| **Python Package** | No official SDK; use `requests` |
| **Ease of Integration** | 3/5 - Good API but pricing is opaque and sales-driven |
| **Project Fit** | High quality news data but expensive. The "Why Is It Moving" feature is unique. Better suited for real-time trading than mid-term analysis. |

---

### 2.5 StockGeist

| Field | Details |
|---|---|
| **URL** | https://www.stockgeist.ai |
| **Data Provided** | Social media sentiment for 2,200+ US stocks. Extracts from Reddit and X/Twitter. |
| **Free Tier** | Limited credits on signup |
| **Paid Tiers** | Credit-based: $0.0001 per credit. Flexible scaling. |
| **API Quality** | REST + streaming. JSON output. |
| **Python Package** | No official SDK |
| **Ease of Integration** | 3/5 - Clean API but credit-based pricing is hard to predict |
| **Project Fit** | Interesting for social sentiment features. Niche - only useful if you specifically want Reddit/Twitter sentiment signals. Finnhub's social sentiment endpoint may be sufficient. |

---

### 2.6 Reddit / X (Twitter) APIs

| Field | Details |
|---|---|
| **Reddit API** | https://www.reddit.com/dev/api/ - Free tier: 100 req/min. Monitor r/wallstreetbets, r/stocks, r/investing. Python: `praw`. |
| **X/Twitter API** | https://developer.x.com - Free: 1,500 tweets/mo read. Basic: $200/mo (10k tweets). Pro: $5,000/mo. Python: `tweepy`. |
| **Project Fit** | Reddit is viable (free, active finance community). Twitter/X is too expensive for the data value. Consider using Finnhub's pre-processed social sentiment instead. |

---

## 3. Fundamental Data Providers

### 3.1 Financial Modeling Prep (FMP)

| Field | Details |
|---|---|
| **URL** | https://site.financialmodelingprep.com |
| **Data Provided** | Income statements, balance sheets, cash flows, ratios, earnings estimates, analyst ratings, institutional holdings, ESG, commodities, ETF holdings, 13F filings |
| **Free Tier** | 250 req/day. ~5 year history. 150+ endpoints. 500MB/30 days bandwidth. |
| **Paid Tiers** | Starter: $19/mo (real-time US, 20GB bandwidth). Premium: $49/mo (UK/Canada, intraday, 50GB). Ultimate: $99/mo (global, transcripts, 13F, 150GB). |
| **API Quality** | REST + WebSocket. Clean JSON. Consistent schema. |
| **History Depth** | 30+ years of fundamental data, 46 countries |
| **Python Package** | `fmpsdk` (community) |
| **Ease of Integration** | 5/5 - Cleanest fundamentals API available. Consistent naming, easy to parse. |
| **Project Fit** | Excellent. The $19/mo Starter plan gives you everything needed for ML features: earnings surprises, PE ratios, revenue growth, analyst estimates. Covers SLV (ETF holdings) and AMD (full financials). |

**Key endpoints for this project:**
- `/income-statement/AMD` - quarterly/annual financials
- `/analyst-estimates/AMD` - forward estimates
- `/earnings-surprises/AMD` - beat/miss history
- `/ratios/AMD` - PE, PB, debt ratios
- `/etf-holder/SLV` - ETF composition

---

### 3.2 Finnhub (Fundamentals)

| Field | Details |
|---|---|
| **URL** | https://finnhub.io |
| **Data Provided** | Basic financials, earnings, insider transactions, SEC filings, ownership |
| **Free Tier** | Basic fundamentals included in free tier |
| **Paid Tiers** | Fundamental Data: $50/mo. Fundamental Data Plus: $200/mo. |
| **Project Fit** | Good for basics. FMP is better for comprehensive fundamentals. Use Finnhub's free tier for insider trading and ownership data. |

---

### 3.3 SimFin

| Field | Details |
|---|---|
| **URL** | https://www.simfin.com |
| **Data Provided** | Income statements, balance sheets, cash flows, share prices, ratios for ~4,000 US stocks |
| **Free Tier** | Free registration. Bulk CSV downloads. Limited history. |
| **Paid Tiers** | SimFin+: pricing on their site (estimated $10-30/mo). Extended history, more companies, daily ratios since 2003. |
| **Python Package** | `simfin` (official, pandas-native) |
| **Ease of Integration** | 4/5 - Downloads bulk data as CSV, loads into pandas DataFrames automatically. Great for offline analysis. |
| **Project Fit** | Good budget option for fundamentals. The bulk download approach is nice for backtesting (no API rate limits). Less comprehensive than FMP. |

---

### 3.4 SEC EDGAR

| Field | Details |
|---|---|
| **URL** | https://www.sec.gov/edgar |
| **Data Provided** | Raw SEC filings: 10-K, 10-Q, 8-K, insider transactions (Form 4), institutional holdings (13F) |
| **Free Tier** | Completely free. 10 req/sec with User-Agent header. |
| **Paid Tiers** | N/A - government data |
| **API Quality** | REST (EDGAR full-text search, XBRL structured data). JSON for company facts API. |
| **Python Package** | `sec-edgar-downloader`, `edgartools`, `sec-api` (paid wrapper) |
| **Ease of Integration** | 2/5 - Raw filings require significant parsing. The XBRL/company facts API is cleaner but still requires domain knowledge. |
| **Project Fit** | Use for insider trading signals (Form 4) and institutional ownership (13F). For standard financials, FMP or SimFin are much easier. |

---

### 3.5 Intrinio

| Field | Details |
|---|---|
| **URL** | https://intrinio.com |
| **Data Provided** | US/global equities, fundamentals (standardized + as-reported), options, ETFs, ESG |
| **Free Tier** | Free trial available |
| **Paid Tiers** | Bronze: ~$200/mo (EOD prices + fundamentals). Silver: ~$400/mo. Gold: ~$800/mo (real-time). Options from $150-1,600/mo. |
| **History Depth** | Back to 1996+ (some to 1970s) |
| **Python Package** | `intrinio-sdk` (official) |
| **Ease of Integration** | 3/5 - Good SDK but pricing is complex (subscribe per data feed) |
| **Project Fit** | Expensive for individual use. Better suited for institutional users. FMP offers similar data at 1/10th the price. |

---

### 3.6 IEX Cloud (DISCONTINUED)

> **Status: Shut down August 2024.** IEX Cloud is no longer operational. Former users have migrated to Alpha Vantage, FMP, and Polygon. Do not use `iexfinance` or IEX Cloud API keys - they will not work.

---

## 4. Macro & Economic Data Providers

### 4.1 FRED (Federal Reserve Economic Data)

| Field | Details |
|---|---|
| **URL** | https://fred.stlouisfed.org |
| **Data Provided** | 800,000+ economic time series: GDP, CPI, unemployment, interest rates, yield curves, money supply, housing, industrial production, consumer sentiment, VIX, commodity prices |
| **Free Tier** | Completely free. Requires API key (instant, free registration). |
| **Paid Tiers** | N/A - all free |
| **API Quality** | REST. JSON/XML. Well-documented. |
| **Rate Limits** | 120 req/min (very generous) |
| **History Depth** | Decades to 100+ years depending on series |
| **Python Package** | `fredapi` (popular, pandas-native), `fedfred` (newer, async support, caching) |
| **Ease of Integration** | 5/5 - `fredapi` returns pandas Series/DataFrames directly. Search by keyword. |
| **Project Fit** | Essential. Free, comprehensive, reliable. Already partially used in this project for VIX. |

**Key series for this project:**
- `VIXCLS` - VIX (already used)
- `DFF` - Fed Funds Rate
- `T10Y2Y` - 10Y-2Y yield spread (recession indicator)
- `CPIAUCSL` - CPI (inflation)
- `UNRATE` - Unemployment rate
- `GOLDAMGBD228NLBM` - Gold price (relevant for SLV)
- `DCOILWTICO` - WTI Crude Oil
- `NASDAQCOM` - Nasdaq Composite
- `UMCSENT` - Consumer Sentiment

---

### 4.2 Nasdaq Data Link (for Macro)

| Field | Details |
|---|---|
| **URL** | https://data.nasdaq.com |
| **Data Provided** | Curated macro datasets, commodities, futures curves, proprietary indicators |
| **Free Tier** | Some free datasets. 300 req/10sec. |
| **Paid Tiers** | Premium datasets $500+/mo. |
| **Python Package** | `nasdaqdatalink` |
| **Project Fit** | Only if you need specific premium datasets (e.g., CFTC Commitments of Traders for commodities/SLV). For standard macro, FRED is free and better. |

---

### 4.3 World Bank API

| Field | Details |
|---|---|
| **URL** | https://data.worldbank.org |
| **Data Provided** | Global development indicators: GDP by country, trade flows, population, etc. |
| **Free Tier** | Completely free. No API key required. |
| **Python Package** | `wbgapi`, `world_bank_data` |
| **Ease of Integration** | 4/5 |
| **Project Fit** | Low priority. Useful for global macro context but too low-frequency (annual/quarterly) for trading signals. |

---

### 4.4 Bureau of Labor Statistics (BLS)

| Field | Details |
|---|---|
| **URL** | https://www.bls.gov/developers/ |
| **Data Provided** | Employment, CPI, PPI, wages, productivity |
| **Free Tier** | Free. 25 req/day without key, 500/day with free key. |
| **Python Package** | `bls` (community) |
| **Project Fit** | Low priority. FRED mirrors most BLS data with a better API. Use FRED instead. |

---

### 4.5 Geopolitical Risk Index (Caldara-Iacoviello)

| Field | Details |
|---|---|
| **URL** | https://www.matteoiacoviello.com/gpr.htm |
| **Data Provided** | Monthly Geopolitical Risk Index (GPR) since 1985. Historical index since 1900. Country-specific indexes. |
| **Free Tier** | Completely free. Direct CSV/Excel download. |
| **API Quality** | No API - downloadable files only (CSV). Must be manually refreshed. |
| **Python Package** | None - load with `pandas.read_csv()` or `pandas.read_excel()` |
| **Ease of Integration** | 3/5 - Simple download but no API means manual refresh |
| **Project Fit** | Interesting macro risk indicator. Monthly frequency limits usefulness for short-term signals but good for regime detection in mid-term analysis. |

---

## 5. Alternative Data Providers

### 5.1 Unusual Whales

| Field | Details |
|---|---|
| **URL** | https://unusualwhales.com |
| **Data Provided** | Real-time options flow, dark pool data, congressional trading, institutional holdings, earnings whispers, technical indicators |
| **Free Tier** | Limited free access |
| **Paid Tiers** | Options flow data: $250/mo (full market). Platform subscription separate. 10% discount for 1yr+. Enterprise pricing available. |
| **API Quality** | REST + WebSocket + Kafka + MCP Server. 100+ endpoints. |
| **Python Package** | No official SDK; REST API with `requests`. MCP server available. |
| **Ease of Integration** | 3/5 - Good API docs, but expensive |
| **Project Fit** | High value for options-flow based signals. Congressional trading data is unique alpha. Expensive at $250/mo. Consider Quiver Quantitative for cheaper congressional data. |

**Unique features:**
- Real-time unusual options activity (large block trades, sweeps)
- Dark pool volume and prints
- Congressional stock trading disclosures
- Institutional 13F holdings with change tracking

---

### 5.2 Quiver Quantitative

| Field | Details |
|---|---|
| **URL** | https://www.quiverquant.com |
| **Data Provided** | Congressional trading, corporate lobbying, government contracts, insider trading, Wikipedia trends, patent filings, social media mentions |
| **Free Tier** | Limited access |
| **Paid Tiers** | Hobbyist: ~$10/mo. Trader: ~$25/mo ($300/yr). Institution: custom. 7-day free trial (monthly) or 30-day (annual). |
| **API Quality** | REST. JSON. Clean endpoints. |
| **History Depth** | Congressional trading since 2016. Lobbying and contracts data varies. |
| **Python Package** | `quiverquant` (official) |
| **Ease of Integration** | 4/5 - Clean API, official Python package, well-documented |
| **Project Fit** | Interesting alternative data at a reasonable price. Congressional trading signals have shown alpha in academic research. The $10/mo Hobbyist plan is a cheap experiment. AMD likely has congressional trading activity. |

---

### 5.3 Estimize

| Field | Details |
|---|---|
| **URL** | https://www.estimize.com |
| **Data Provided** | Crowdsourced earnings estimates (EPS + revenue). Consensus from buy-side analysts, independent researchers, and students. |
| **Free Tier** | Website access only |
| **Paid Tiers** | Institutional licensing only (contact sales). 30-day API trial available. |
| **API Quality** | REST API (limited documentation) |
| **Python Package** | None |
| **Ease of Integration** | 2/5 - Institutional sales process, no self-serve |
| **Project Fit** | Interesting concept (crowdsourced estimates often beat Wall Street). But institutional pricing and lack of self-serve API make it impractical for individual use. FMP's analyst estimates are a better alternative. |

---

## 6. Recommended Stack for This Project

### Context
This project performs mid-term stock analysis with ML, focusing on SLV (precious metals ETF) and AMD (semiconductor). It needs: historical prices, technical indicators, sentiment/news features, fundamental data, and macro indicators.

### Recommended Stack

| Layer | Provider | Plan | Monthly Cost | What It Covers |
|---|---|---|---|---|
| **Prices** | Alpaca Markets | Free | $0 | 7+ yr intraday OHLCV for SLV, AMD, benchmarks |
| **Prices (backup)** | Tiingo | Free | $0 | 30+ yr daily data, cross-validation |
| **Sentiment & News** | Finnhub | Free | $0 | Analyst recs, news, insider trading, social sentiment, earnings calendar |
| **Fundamentals** | FMP | Starter | $19 | Earnings, financials, estimates, ratios, ETF holdings |
| **Macro** | FRED | Free | $0 | VIX, yield curve, CPI, gold price, unemployment, Fed funds rate |
| **Alternative** | Quiver Quantitative | Hobbyist | $10 | Congressional trading, lobbying, government contracts |
| **Geopolitical** | GPR Index | Free download | $0 | Monthly geopolitical risk index |
| **Total** | | | **$29/mo** | |

### Upgrade Path (if budget allows)

| Upgrade | Cost Delta | Benefit |
|---|---|---|
| Polygon Stocks Basic | +$29/mo | Tick-level data, better intraday resolution |
| Finnhub Fundamental Data | +$50/mo | Deeper fundamentals, estimates |
| FMP Premium | +$30/mo | Intraday charts, technical indicators, UK/Canada |
| Unusual Whales | +$250/mo | Options flow signals (high-value but expensive) |

---

## 7. Integration Priority

### Phase 1: Replace yfinance (Week 1-2)
**Goal:** Eliminate dependency on unreliable yfinance.

1. **Alpaca Markets** - Replace `yfinance` for all OHLCV downloads
   - Sign up at https://alpaca.markets (free)
   - `pip install alpaca-py`
   - Migrate `scripts/download_prices.py` to use Alpaca's `StockHistoricalDataClient`
   - Get 7+ years of 1-min/5-min/daily bars for SLV, AMD, and benchmarks

2. **FRED** - Already partially integrated (VIX). Expand to:
   - Yield curve (T10Y2Y)
   - Gold price (for SLV correlation)
   - CPI, unemployment, Fed funds rate
   - `pip install fredapi`

### Phase 2: Add Sentiment Features (Week 3-4)
**Goal:** New ML features from news/sentiment data.

3. **Finnhub** - Add sentiment and analyst data
   - `pip install finnhub-python`
   - Pull analyst recommendation trends (buy/hold/sell counts over time)
   - Pull insider transaction data (net insider buying/selling)
   - Pull earnings calendar and surprise history
   - Create rolling sentiment features for ML model

### Phase 3: Add Fundamentals (Week 5-6)
**Goal:** Fundamental features for ML.

4. **FMP** - Add earnings and financial data
   - `pip install fmpsdk` or use `requests` directly
   - Pull quarterly earnings surprises (actual vs estimate)
   - Pull key ratios (PE, PB, debt/equity)
   - Pull revenue/earnings growth rates
   - For SLV: pull ETF holdings data (gold/silver exposure breakdown)
   - For AMD: pull semiconductor cycle indicators

### Phase 4: Alternative Data (Week 7-8)
**Goal:** Experimental alpha signals.

5. **Quiver Quantitative** - Congressional trading signals
   - `pip install quiverquant`
   - Track congressional purchases/sales of AMD
   - Create binary features: "congress_buying_AMD_30d" etc.

6. **GPR Index** - Geopolitical risk regime
   - Download CSV from matteoiacoviello.com/gpr.htm
   - Create regime indicator (high/low geopolitical risk)
   - Especially relevant for SLV (safe-haven asset)

### Phase 5: Optional Upgrades (Month 3+)
Evaluate based on model performance whether Polygon tick data or Unusual Whales options flow data would improve predictions enough to justify their cost.

---

## Appendix: Python Package Quick Reference

```bash
# Price Data
pip install alpaca-py              # Alpaca Markets (primary)
pip install polygon                # Polygon.io / Massive
pip install alpha_vantage          # Alpha Vantage
pip install eodhd                  # EOD Historical Data
pip install nasdaqdatalink         # Nasdaq Data Link / Quandl
pip install yfinance               # Yahoo Finance (legacy, unreliable)

# Sentiment & News
pip install finnhub-python         # Finnhub (sentiment, news, fundamentals)
pip install newsapi-python         # NewsAPI (general news)
pip install praw                   # Reddit API (r/wallstreetbets)
pip install tweepy                 # X/Twitter API

# Fundamentals
pip install simfin                 # SimFin
pip install sec-edgar-downloader   # SEC EDGAR filings
pip install edgartools              # SEC EDGAR (newer, friendlier)

# Macro
pip install fredapi                # FRED (Federal Reserve)
pip install fedfred                # FRED (newer, async + caching)
pip install wbgapi                 # World Bank

# Alternative Data
pip install quiverquant            # Quiver Quantitative

# Broker APIs
pip install ib_insync              # Interactive Brokers (async wrapper)
pip install schwab-py              # Charles Schwab
```

---

## Appendix: Data Freshness & Update Frequency

| Provider | Real-Time | 15-Min Delay | EOD | Fundamental Updates |
|---|---|---|---|---|
| Alpaca (paid) | Yes (WebSocket) | Yes (free) | Yes | N/A |
| Polygon (paid) | Yes (WebSocket) | N/A | Yes | N/A |
| Finnhub | Yes (WebSocket, 50 sym free) | Yes | Yes | Quarterly |
| FMP (paid) | Yes (WebSocket) | N/A | Yes | Quarterly |
| FRED | N/A | N/A | Varies (daily-monthly) | Per series schedule |
| yfinance | Delayed | Delayed | Yes | Unreliable |

---

*This document should be reviewed quarterly as provider pricing and features change frequently. IEX Cloud's shutdown in Aug 2024 is a reminder that providers can disappear with little warning - always have a backup data source.*

---

## See Also

- [API key setup](api-configuration.md)
- [Fundamental data sources](fundamentals-data-sources.md)
- [Data pipeline](data-engineering.md)
