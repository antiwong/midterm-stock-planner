#!/usr/bin/env python3
"""Cross-Asset Correlation Analysis for AMD and SLV.

Analyzes correlations between:
- AMD and tech/AI/semiconductor stocks and indexes
- SLV and precious metals, VIX, DXY (dollar index)

Usage:
    python scripts/correlation_analysis.py
    python scripts/correlation_analysis.py --ticker AMD --peers NVDA GOOGL MSFT
    python scripts/correlation_analysis.py --ticker SLV --peers GLD GDX
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))


def load_data(price_path: str = "data/prices.csv") -> pd.DataFrame:
    """Load existing price data."""
    df = pd.read_csv(price_path, parse_dates=["date"])
    return df


def fetch_additional_data(tickers: list, start: str, end: str) -> pd.DataFrame:
    """Fetch additional comparison data via yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance required: pip install yfinance")
        return pd.DataFrame()

    all_data = []
    for ticker in tickers:
        try:
            data = yf.download(ticker, start=start, end=end, interval="1h",
                             auto_adjust=True, progress=False)
            if data.empty:
                # Try daily if hourly not available
                data = yf.download(ticker, start=start, end=end,
                                 auto_adjust=True, progress=False)
            if not data.empty:
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                data = data.reset_index()
                data.columns = [c.lower() for c in data.columns]
                if "datetime" in data.columns:
                    data = data.rename(columns={"datetime": "date"})
                data["ticker"] = ticker.replace("^", "").replace("-", "_")
                all_data.append(data[["date", "ticker", "close"]].copy())
                print(f"  Fetched {ticker}: {len(data)} rows")
        except Exception as e:
            print(f"  Warning: Could not fetch {ticker}: {e}")

    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()


def compute_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Compute daily returns per ticker from close prices."""
    pivoted = df.pivot_table(index="date", columns="ticker", values="close")
    # For hourly data, get daily close (last bar per day)
    pivoted.index = pd.to_datetime(pivoted.index)
    daily = pivoted.resample("D").last().dropna(how="all")
    returns = daily.pct_change().dropna(how="all")
    return returns


def correlation_matrix(returns: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
    """Compute correlation matrix."""
    return returns.corr(method=method)


def rolling_correlation(returns: pd.DataFrame, ticker1: str, ticker2: str,
                       window: int = 20) -> pd.Series:
    """Compute rolling correlation between two tickers."""
    if ticker1 not in returns.columns or ticker2 not in returns.columns:
        return pd.Series(dtype=float)
    return returns[ticker1].rolling(window).corr(returns[ticker2])


def cross_correlation(returns: pd.DataFrame, ticker1: str, ticker2: str,
                     max_lag: int = 5) -> dict:
    """Compute cross-correlation with lags.

    Positive lag = ticker2 leads ticker1.
    Negative lag = ticker1 leads ticker2.
    """
    if ticker1 not in returns.columns or ticker2 not in returns.columns:
        return {}

    s1 = returns[ticker1].dropna()
    s2 = returns[ticker2].dropna()

    # Align
    common = s1.index.intersection(s2.index)
    s1 = s1.loc[common]
    s2 = s2.loc[common]

    results = {}
    for lag in range(-max_lag, max_lag + 1):
        if lag == 0:
            corr = s1.corr(s2)
        elif lag > 0:
            corr = s1.iloc[lag:].reset_index(drop=True).corr(
                s2.iloc[:-lag].reset_index(drop=True)
            )
        else:
            corr = s1.iloc[:lag].reset_index(drop=True).corr(
                s2.iloc[-lag:].reset_index(drop=True)
            )
        results[lag] = round(corr, 4) if not np.isnan(corr) else 0.0

    return results


def analyze_amd(price_df: pd.DataFrame, additional_df: pd.DataFrame = None) -> dict:
    """Full AMD correlation analysis."""
    # Combine data
    dfs = [price_df[price_df["ticker"].isin(["AMD", "NVDA", "GOOGL", "MSFT", "META", "TSLA", "AAPL", "AMZN"])]]
    if additional_df is not None and not additional_df.empty:
        dfs.append(additional_df)
    combined = pd.concat(dfs, ignore_index=True)

    returns = compute_returns(combined)

    results = {
        "ticker": "AMD",
        "peers": [c for c in returns.columns if c != "AMD"],
        "pearson_correlation": {},
        "spearman_correlation": {},
        "rolling_20d": {},
        "rolling_60d": {},
        "lead_lag": {},
    }

    if "AMD" not in returns.columns:
        return results

    # Correlation matrices
    pearson = correlation_matrix(returns, "pearson")
    spearman = correlation_matrix(returns, "spearman")

    if "AMD" in pearson.index:
        results["pearson_correlation"] = pearson.loc["AMD"].drop("AMD", errors="ignore").to_dict()
        results["spearman_correlation"] = spearman.loc["AMD"].drop("AMD", errors="ignore").to_dict()

    # Rolling correlations
    for peer in results["peers"]:
        r20 = rolling_correlation(returns, "AMD", peer, 20)
        r60 = rolling_correlation(returns, "AMD", peer, 60)
        results["rolling_20d"][peer] = {
            "mean": round(r20.mean(), 4) if not r20.empty else 0,
            "std": round(r20.std(), 4) if not r20.empty else 0,
            "min": round(r20.min(), 4) if not r20.empty else 0,
            "max": round(r20.max(), 4) if not r20.empty else 0,
        }
        results["rolling_60d"][peer] = {
            "mean": round(r60.mean(), 4) if not r60.empty else 0,
            "std": round(r60.std(), 4) if not r60.empty else 0,
        }

    # Lead-lag
    for peer in results["peers"]:
        results["lead_lag"][peer] = cross_correlation(returns, "AMD", peer, max_lag=5)

    return results


def analyze_slv(price_df: pd.DataFrame, additional_df: pd.DataFrame = None) -> dict:
    """Full SLV correlation analysis."""
    dfs = [price_df[price_df["ticker"].isin(["SLV"])]]
    if additional_df is not None and not additional_df.empty:
        dfs.append(additional_df)
    combined = pd.concat(dfs, ignore_index=True)

    returns = compute_returns(combined)

    results = {
        "ticker": "SLV",
        "peers": [c for c in returns.columns if c != "SLV"],
        "pearson_correlation": {},
        "spearman_correlation": {},
        "rolling_20d": {},
        "rolling_60d": {},
        "lead_lag": {},
    }

    if "SLV" not in returns.columns:
        return results

    pearson = correlation_matrix(returns, "pearson")
    spearman = correlation_matrix(returns, "spearman")

    if "SLV" in pearson.index:
        results["pearson_correlation"] = pearson.loc["SLV"].drop("SLV", errors="ignore").to_dict()
        results["spearman_correlation"] = spearman.loc["SLV"].drop("SLV", errors="ignore").to_dict()

    for peer in results["peers"]:
        r20 = rolling_correlation(returns, "SLV", peer, 20)
        r60 = rolling_correlation(returns, "SLV", peer, 60)
        results["rolling_20d"][peer] = {
            "mean": round(r20.mean(), 4) if not r20.empty else 0,
            "std": round(r20.std(), 4) if not r20.empty else 0,
            "min": round(r20.min(), 4) if not r20.empty else 0,
            "max": round(r20.max(), 4) if not r20.empty else 0,
        }
        results["rolling_60d"][peer] = {
            "mean": round(r60.mean(), 4) if not r60.empty else 0,
            "std": round(r60.std(), 4) if not r60.empty else 0,
        }

    for peer in results["peers"]:
        results["lead_lag"][peer] = cross_correlation(returns, "SLV", peer, max_lag=5)

    return results


def generate_report(amd_results: dict, slv_results: dict, output_path: str) -> str:
    """Generate comprehensive Markdown correlation report."""
    lines = []
    lines.append("# Cross-Asset Correlation Analysis")
    lines.append(f"\n**Generated**: {datetime.now().isoformat()}")

    # ── AMD Section ──
    lines.append("\n---\n## AMD — Tech/AI/Semiconductor Correlations\n")
    lines.append("### Static Correlations (Full Period)\n")
    lines.append("| Peer | Pearson | Spearman | Interpretation |")
    lines.append("|------|---------|----------|----------------|")

    for peer in sorted(amd_results["pearson_correlation"].keys()):
        p = amd_results["pearson_correlation"].get(peer, 0)
        s = amd_results["spearman_correlation"].get(peer, 0)
        if abs(p) > 0.7:
            interp = "Strong"
        elif abs(p) > 0.4:
            interp = "Moderate"
        elif abs(p) > 0.2:
            interp = "Weak"
        else:
            interp = "Negligible"
        direction = "positive" if p > 0 else "negative"
        lines.append(f"| {peer} | {p:.4f} | {s:.4f} | {interp} {direction} |")

    # Rolling stability
    lines.append("\n### Rolling Correlation Stability (20-day window)\n")
    lines.append("| Peer | Mean | Std | Min | Max | Stability |")
    lines.append("|------|------|-----|-----|-----|-----------|")
    for peer in sorted(amd_results["rolling_20d"].keys()):
        r = amd_results["rolling_20d"][peer]
        stability = "Stable" if r["std"] < 0.15 else "Unstable" if r["std"] > 0.25 else "Moderate"
        lines.append(f"| {peer} | {r['mean']:.4f} | {r['std']:.4f} | {r['min']:.4f} | {r['max']:.4f} | {stability} |")

    # Lead-lag
    lines.append("\n### Lead-Lag Analysis (Cross-Correlation)\n")
    lines.append("Positive lag = peer leads AMD. Peak at lag 0 = synchronous.\n")
    for peer in sorted(amd_results["lead_lag"].keys()):
        lags = amd_results["lead_lag"][peer]
        if not lags:
            continue
        peak_lag = max(lags, key=lambda k: abs(lags[k]))
        peak_corr = lags[peak_lag]
        lag0 = lags.get(0, 0)
        if peak_lag != 0 and abs(peak_corr) > abs(lag0) + 0.02:
            lines.append(f"- **{peer}**: Peak at lag={peak_lag} (r={peak_corr:.4f}). "
                        f"{'Peer leads AMD' if peak_lag > 0 else 'AMD leads peer'} by {abs(peak_lag)} day(s).")
        else:
            lines.append(f"- **{peer}**: Synchronous (lag=0, r={lag0:.4f})")

    # AMD insights
    lines.append("\n### AMD Key Insights\n")
    lines.append("1. **Sector correlation**: AMD typically moves with NVDA (semiconductor peer) "
                "and broader tech (GOOGL, MSFT, META) — shared AI/data center demand driver.")
    lines.append("2. **Index tracking**: QQQ (NASDAQ-100) and SMH (Semiconductor ETF) are "
                "natural benchmarks. High correlation with SMH suggests semiconductor cycle exposure.")
    lines.append("3. **News/sentiment gap**: Tech/AI news sentiment (earnings, chip demand, "
                "AI capex announcements) would add alpha. Consider: Finnhub news sentiment, "
                "Reddit/Twitter sentiment on $AMD, AI investment news flow.")
    lines.append("4. **Recommended new features for regression testing**:")
    lines.append("   - `peer_momentum_nvda`: NVDA relative strength (leads AMD in some cycles)")
    lines.append("   - `sector_breadth_semis`: % of semiconductor stocks above 50d SMA")
    lines.append("   - `ai_news_sentiment`: NLP sentiment on AI/chip news")
    lines.append("   - `qqq_relative_strength`: AMD performance relative to QQQ")

    # ── SLV Section ──
    lines.append("\n---\n## SLV — Precious Metals / Macro Correlations\n")
    lines.append("### Static Correlations (Full Period)\n")
    lines.append("| Peer | Pearson | Spearman | Interpretation |")
    lines.append("|------|---------|----------|----------------|")

    for peer in sorted(slv_results["pearson_correlation"].keys()):
        p = slv_results["pearson_correlation"].get(peer, 0)
        s = slv_results["spearman_correlation"].get(peer, 0)
        if abs(p) > 0.7:
            interp = "Strong"
        elif abs(p) > 0.4:
            interp = "Moderate"
        elif abs(p) > 0.2:
            interp = "Weak"
        else:
            interp = "Negligible"
        direction = "positive" if p > 0 else "negative (inverse)"
        lines.append(f"| {peer} | {p:.4f} | {s:.4f} | {interp} {direction} |")

    lines.append("\n### Rolling Correlation Stability (20-day window)\n")
    lines.append("| Peer | Mean | Std | Min | Max | Stability |")
    lines.append("|------|------|-----|-----|-----|-----------|")
    for peer in sorted(slv_results["rolling_20d"].keys()):
        r = slv_results["rolling_20d"][peer]
        stability = "Stable" if r["std"] < 0.15 else "Unstable" if r["std"] > 0.25 else "Moderate"
        lines.append(f"| {peer} | {r['mean']:.4f} | {r['std']:.4f} | {r['min']:.4f} | {r['max']:.4f} | {stability} |")

    lines.append("\n### Lead-Lag Analysis\n")
    for peer in sorted(slv_results["lead_lag"].keys()):
        lags = slv_results["lead_lag"][peer]
        if not lags:
            continue
        peak_lag = max(lags, key=lambda k: abs(lags[k]))
        peak_corr = lags[peak_lag]
        lag0 = lags.get(0, 0)
        if peak_lag != 0 and abs(peak_corr) > abs(lag0) + 0.02:
            lines.append(f"- **{peer}**: Peak at lag={peak_lag} (r={peak_corr:.4f}). "
                        f"{'Peer leads SLV' if peak_lag > 0 else 'SLV leads peer'} by {abs(peak_lag)} day(s).")
        else:
            lines.append(f"- **{peer}**: Synchronous (lag=0, r={lag0:.4f})")

    # SLV insights
    lines.append("\n### SLV Key Insights\n")
    lines.append("1. **Precious metals correlation**: SLV (silver) typically correlates strongly with "
                "GLD (gold) but with higher beta. Gold leads silver in risk-off moves.")
    lines.append("2. **Dollar inverse**: DXY (US Dollar Index) has a historically negative correlation "
                "with precious metals. Dollar strength = metals weakness. Already captured via DXY optimization.")
    lines.append("3. **Fear gauge**: VIX (volatility) correlation with SLV is typically positive in "
                "crisis periods (safe haven demand) but can decouple. Already captured via VIX optimization.")
    lines.append("4. **Geopolitical/war gap**: War, sanctions, and geopolitical tension drive precious "
                "metals demand. No automated geopolitical risk indicator in the system currently.")
    lines.append("5. **Recommended new features for regression testing**:")
    lines.append("   - `gold_silver_ratio`: GLD/SLV ratio (mean-reverts, signals relative value)")
    lines.append("   - `dxy_momentum`: Dollar momentum (inverse signal for metals)")
    lines.append("   - `vix_regime`: VIX regime classification (low/medium/high volatility)")
    lines.append("   - `geopolitical_risk_index`: GPR index from Caldara & Iacoviello (publicly available)")
    lines.append("   - `real_yield_10y`: 10Y Treasury yield - inflation expectations (key metals driver)")
    lines.append("   - `mining_etf_breadth`: % of mining stocks above 50d SMA")

    # ── Summary Recommendations ──
    lines.append("\n---\n## Summary: Recommended Feature Additions\n")
    lines.append("### For AMD (Tech/Semiconductor)")
    lines.append("| Feature | Source | Expected Impact |")
    lines.append("|---------|--------|----------------|")
    lines.append("| NVDA relative strength | Calculated from prices | High — strongest peer correlation |")
    lines.append("| Semiconductor sector breadth | SMH holdings | Medium — sector health |")
    lines.append("| Tech/AI news sentiment | Finnhub / NewsAPI + NLP | High — earnings and AI capex catalysts |")
    lines.append("| QQQ relative performance | Calculated from prices | Medium — broad tech benchmark |")
    lines.append("\n### For SLV (Precious Metals)")
    lines.append("| Feature | Source | Expected Impact |")
    lines.append("|---------|--------|----------------|")
    lines.append("| Gold/Silver ratio | GLD/SLV prices | High — mean-reverting signal |")
    lines.append("| DXY momentum & regime | DXY prices | High — inverse correlation driver |")
    lines.append("| VIX regime classification | VIX prices | Medium — fear-driven demand |")
    lines.append("| Geopolitical risk index | Caldara-Iacoviello GPR | High — war/sanctions premium |")
    lines.append("| Real yield 10Y | FRED / Treasury data | High — opportunity cost of holding metals |")
    lines.append("| Mining ETF breadth | GDX/GDXJ holdings | Medium — sector participation |")

    content = "\n".join(lines)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(content)

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Cross-Asset Correlation Analysis")
    parser.add_argument("--price-path", default="data/prices.csv", help="Price data path")
    parser.add_argument("--output", "-o", default="output/correlation_analysis.md", help="Output report path")
    parser.add_argument("--no-fetch", action="store_true", help="Skip fetching additional data")
    args = parser.parse_args()

    print("Loading price data...")
    price_df = load_data(args.price_path)

    date_min = str(price_df["date"].min().date())
    date_max = str(price_df["date"].max().date())
    print(f"Date range: {date_min} to {date_max}")

    additional_df = pd.DataFrame()
    if not args.no_fetch:
        print("\nFetching additional comparison data...")
        # Tickers to fetch that aren't in our price data
        existing_tickers = set(price_df["ticker"].unique())
        needed = []
        for t in ["QQQ", "SMH", "GLD", "GDX", "^VIX", "DX-Y.NYB"]:
            clean = t.replace("^", "").replace("-", "_").replace(".", "_")
            if clean not in existing_tickers:
                needed.append(t)

        if needed:
            additional_df = fetch_additional_data(needed, date_min, date_max)

    # Run analyses
    print("\nAnalyzing AMD correlations...")
    amd_results = analyze_amd(price_df, additional_df)

    print("Analyzing SLV correlations...")
    slv_results = analyze_slv(price_df, additional_df)

    # Store in database
    print("\nStoring correlations in database...")
    try:
        from src.regression.database import RegressionDatabase
        import json
        db = RegressionDatabase("data/runs.db")
        analysis_id = f"corr_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        for ticker, results in [("AMD", amd_results), ("SLV", slv_results)]:
            for peer in results.get("pearson_correlation", {}):
                db.log_correlation_analysis(
                    analysis_id=f"{analysis_id}_{ticker}_{peer}",
                    ticker=ticker,
                    peer_ticker=peer,
                    pearson_corr=results["pearson_correlation"].get(peer),
                    spearman_corr=results["spearman_correlation"].get(peer),
                    rolling_20d_mean=results.get("rolling_20d", {}).get(peer, {}).get("mean"),
                    rolling_20d_std=results.get("rolling_20d", {}).get(peer, {}).get("std"),
                    rolling_60d_mean=results.get("rolling_60d", {}).get(peer, {}).get("mean"),
                    rolling_60d_std=results.get("rolling_60d", {}).get(peer, {}).get("std"),
                    lead_lag=results.get("lead_lag", {}).get(peer),
                )
        print(f"  Stored correlations for AMD and SLV")
    except Exception as e:
        print(f"  Warning: Could not store in DB: {e}")

    # Generate report
    print("\nGenerating report...")
    report_path = generate_report(amd_results, slv_results, args.output)
    print(f"Report saved to: {report_path}")

    # Print quick summary
    print("\n" + "=" * 60)
    print("QUICK SUMMARY")
    print("=" * 60)

    print("\nAMD Top Correlations:")
    for peer, corr in sorted(amd_results["pearson_correlation"].items(),
                              key=lambda x: abs(x[1]), reverse=True)[:5]:
        print(f"  {peer}: {corr:.4f}")

    print("\nSLV Top Correlations:")
    for peer, corr in sorted(slv_results["pearson_correlation"].items(),
                              key=lambda x: abs(x[1]), reverse=True)[:5]:
        print(f"  {peer}: {corr:.4f}")


if __name__ == "__main__":
    main()
