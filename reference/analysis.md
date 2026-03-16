# Reference Project Analysis

**Date**: 2026-03-16

---

## 1. NoFxAiOS/nofx (Go, LLM-driven trading)

**URL**: https://github.com/NoFxAiOS/nofx/tree/dev

### What It Does
Autonomous AI trading assistant using LLMs (not ML models) as decision-makers. Feeds structured market data into AI prompts, gets back trade decisions with chain-of-thought reasoning. Primarily targets crypto perpetuals, with secondary support for US stocks (Alpaca) and forex/metals (TwelveData).

### Architecture
- **Go backend** with React 18 frontend dashboard
- **Multi-exchange**: Binance, Bybit, OKX, Alpaca, TwelveData (10 connectors)
- **Multi-AI**: DeepSeek, Qwen, GPT, Claude, Gemini via MCP abstraction
- **Live-only**: No backtesting engine; performance tracked via stored metrics

### Key Features
- LLM prompt engineering for trade decisions (system + user prompt with market context)
- Multi-timeframe data assembly with technical indicators (EMA, MACD, RSI, ATR, Bollinger, Donchian)
- OI-price correlation matrix (bullish accumulation, distribution, short covering, long liquidation)
- Confidence-to-position-sizing mapping (85+: 80-100%, 70-84: 50-80%, 60-69: 30-50%, <60: no trade)
- Hard-coded risk rules: max 30% margin, -5% single position stop, -10% daily loss, 30% peak drawdown close

### Applicable to Our Project

| Idea | Applicability | Priority |
|------|--------------|----------|
| **Risk management rules** (drawdown monitor, daily loss limits, position concentration caps) | High — adapt for Alpaca paper trading | P2 |
| **TwelveData as supplementary data source** for forex/metals | Medium — useful for precious metals cross-asset signals | P3 |
| **Confidence-to-sizing mapping** | Medium — adapt LightGBM prediction confidence to modulate position weights | P2 |
| **OI-price correlation for regime detection** | Medium — if options OI data available for our tickers | P3 |
| **LLM as secondary validation layer** | Low — have LLM review model's top picks before execution | P4 |
| Grid trading, crypto connectors, x402 payments | Not applicable | - |

---

## 2. ZhuLinsen/daily_stock_analysis (Python, LLM-driven analysis)

**URL**: https://github.com/ZhuLinsen/daily_stock_analysis

### What It Does
LLM-powered stock analyzer that generates daily "decision dashboards" with buy/sell levels and operation checklists. Supports A-shares (China), Hong Kong, and US stocks. Zero-cost via GitHub Actions automation.

### Architecture
- **Python** with FastAPI web server + multiple bot integrations
- **Multi-agent pipeline**: Technical, Intel, Risk, Strategy, Decision agents (sequential)
- **Multi-source data**: AkShare, Tushare, YFinance, EFinance, Baostock, Stooq (prioritized failover)
- **LLM via LiteLLM**: Gemini, OpenAI, Claude, DeepSeek, Qwen (multi-key load balancing)
- **11 YAML strategy definitions**: Natural-language rules, no coding needed

### Key Features
- 100-point composite scoring: trend (30), deviation (20), volume (15), MACD (15), MA support (10), RSI (10)
- Agent memory system: historical accuracy calibration after 30+ samples
- Risk agent can veto/downgrade signals (buy->hold, hold->sell)
- Social sentiment (Reddit, X, Polymarket) for US stocks
- Strategy win-rate weighting (normalized after 30+ samples)
- Trading day calendar via exchange-calendars

### Applicable to Our Project

| Idea | Applicability | Priority |
|------|--------------|----------|
| **Multi-source data fetcher with failover** (circuit breaker pattern) | High — add Stooq/Alpha Vantage as YFinance fallback | P2 |
| **Historical accuracy calibration loop** (track signal accuracy, adjust confidence) | High — compare LightGBM rankings vs actual returns, feed back into sizing | P1 |
| **Risk override/veto system** (post-ranking guard) | Medium — veto entries on macro regime / drawdown thresholds | P2 |
| **Social sentiment integration** (Reddit/X for US stocks) | Medium — additional feature for tech/semi universe | P3 |
| **YAML strategy definitions** | Low — could define sector rotation rules as YAML | P4 |
| **Trading day calendar** (exchange-calendars) | Low — ensure cron skips holidays | P3 |
| A-share features, WeChat/Feishu notifications | Not applicable | - |

---

## Summary: Top Ideas to Borrow

### Tier 1 (High value, implement next)
1. **Historical accuracy calibration** — Track how well our LightGBM rankings predict actual forward returns. After 30+ trading days, use calibration factor to adjust position sizing. (From: daily_stock_analysis)
2. **Enhanced risk management** — Add drawdown-from-peak monitoring, daily loss limits, and position concentration enforcement to paper trading. (From: nofx)

### Tier 2 (Medium value, implement later)
3. **Data source failover** — Add backup data providers (Stooq, TwelveData) for when Alpaca/YFinance fail. (From: daily_stock_analysis)
4. **Confidence-based position sizing** — Map LightGBM prediction score distribution to position weight tiers instead of equal-weight. (From: nofx)
5. **Social sentiment features** — Integrate Reddit/X sentiment as additional features for the ML model. (From: daily_stock_analysis)

### Tier 3 (Exploratory)
6. **LLM validation layer** — Use Claude/Gemini to review top-5 picks with chain-of-thought before execution. (From: nofx)
7. **OI-price regime detection** — If options data available, classify market regimes for each ticker. (From: nofx)
