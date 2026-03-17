# Requirements

> [← Back to Documentation Index](README.md)

## Functional requirements

1. Data ingestion
   - Load historical price and fundamental data for a configurable stock universe and benchmark.
   - Load news data for sentiment analysis (optional).
   - Refresh data up to the latest available date.

2. Feature engineering
   - Compute factor-style features for each (date, stock) row.
   - Ensure no look-ahead bias when aligning features and labels.
   - Support technical indicators (RSI, MACD, Bollinger Bands, ATR, ADX).
   - Support momentum and mean reversion features.

3. Sentiment analysis (optional)
   - Load and validate news data (timestamp, ticker, headline).
   - Score text using configurable sentiment models (lexicon-based, FinBERT).
   - Aggregate sentiment to daily per-ticker features.
   - Compute rolling sentiment features (mean, std, count, trend).
   - Strict no look-ahead: only use news published before the as-of date.

4. Model training
   - Train a cross-sectional model to predict 3-month forward excess return or return buckets.
   - Support configuration of model type and hyperparameters via code or config file.
   - Include or exclude sentiment features based on configuration.

5. Scoring
   - Given a date and universe, score each stock and return a ranked list.
   - Support scoring with or without sentiment features.

6. Backtesting
   - Run a walk-forward backtest with configurable:
     - Training window length.
     - Test period length.
     - Rebalance frequency (e.g., monthly).
   - Compute performance metrics: CAGR, Sharpe ratio, max drawdown, turnover.
   - Support A/B comparison (with vs. without sentiment features).

7. Explainability
   - Compute SHAP values for trained models.
   - Provide per-stock explanation for a given date and global feature importance.
   - Group features by category (Return, Volatility, Sentiment, etc.).
   - Portfolio-level SHAP aggregation.
   - Analyze sentiment feature contribution.

8. Risk management
   - Position sizing (equal weight, volatility-weighted, score-weighted).
   - Risk metrics (Sharpe, Sortino, Calmar, VaR, CVaR).
   - Portfolio risk monitoring (correlation, sector exposure, risk limits).

9. Visualization
   - Price charts with technical indicators.
   - Equity curves and drawdown charts.
   - Monthly returns heatmap.
   - Correlation matrices.

10. CLI interface
    - Commands:
      - `run-backtest` with config (supports `--use-sentiment`, `--no-sentiment`).
      - `score-latest` for a given universe (supports `--use-sentiment`, `--no-sentiment`).
      - `run-backtest-ab` for A/B comparison with/without sentiment.
      - `compare-sentiment` for analyzing sentiment impact.

## Non-functional requirements

- Code quality:
  - Clear module boundaries and type hints where reasonable.
  - Unit tests for critical components as the project grows.
  - Modular sentiment module that can be extended (e.g., FinBERT, social media).

- Performance:
  - Designed for up to a few thousand stocks with daily data over ~10–20 years.
  - Sentiment scoring: handle thousands of news items efficiently.

- Security & safety:
  - No broker credentials or trading APIs in MVP.
  - For personal research only.

- Configurability:
  - YAML/JSON configuration files.
  - Environment variable overrides.
  - CLI flags for runtime overrides.

## Assumptions

- Data exists locally in CSV/Parquet or can be easily adapted later.
- Universe and benchmark can be configured via a config file or environment variables.
- News data (if used) follows expected schema: timestamp, ticker, headline, optional body/source.
- Sentiment models can be swapped (lexicon → FinBERT) without changing the pipeline.

---

## See Also

- [System architecture](design.md)
- [Quick start setup](quick-start-guide.md)
- [Configuration reference](configuration-cli.md)
