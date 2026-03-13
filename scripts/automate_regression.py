#!/usr/bin/env python3
"""Automated Regression Testing Pipeline.

Runs regression testing across data resolutions, performs gap analysis,
and generates comprehensive reports.

Usage:
    # Full pipeline on current data
    python scripts/automate_regression.py --watchlist tech_giants

    # Gap analysis only
    python scripts/automate_regression.py --gap-analysis-only

    # Multi-resolution (when high-res data available)
    python scripts/automate_regression.py --resolutions 1h 15m 5m --watchlist tech_giants

    # Automated nightly run
    python scripts/automate_regression.py --watchlist tech_giants --tune --output-dir output/nightly
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


# ── Gap Analysis ──────────────────────────────────────────────────────────

class DataGapAnalyzer:
    """Analyze data quality and identify gaps before regression testing."""

    def __init__(self, price_path: str, benchmark_path: str, watchlist_path: str = None):
        self.price_df = pd.read_csv(price_path, parse_dates=["date"])
        self.benchmark_df = pd.read_csv(benchmark_path, parse_dates=["date"])
        self.watchlist_path = watchlist_path
        self.gaps = {}

    def run_full_analysis(self, watchlist_name: str = None) -> dict:
        """Run all gap analysis checks. Returns structured report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "data_summary": self._data_summary(),
            "date_range_gaps": self._check_date_range_gaps(),
            "ticker_coverage": self._check_ticker_coverage(watchlist_name),
            "data_quality": self._check_data_quality(),
            "resolution_analysis": self._check_resolution(),
            "benchmark_alignment": self._check_benchmark_alignment(),
            "recommendations": [],
        }

        # Generate recommendations
        report["recommendations"] = self._generate_recommendations(report)
        report["overall_score"] = self._compute_quality_score(report)

        return report

    def _data_summary(self) -> dict:
        """Basic data summary."""
        df = self.price_df
        return {
            "total_rows": len(df),
            "unique_tickers": sorted(df["ticker"].unique().tolist()),
            "n_tickers": df["ticker"].nunique(),
            "date_range": {
                "start": str(df["date"].min()),
                "end": str(df["date"].max()),
                "span_days": (df["date"].max() - df["date"].min()).days,
            },
            "rows_per_ticker": df.groupby("ticker").size().to_dict(),
            "columns": df.columns.tolist(),
        }

    def _check_date_range_gaps(self) -> dict:
        """Check for gaps in date ranges per ticker."""
        gaps = {}
        df = self.price_df

        for ticker in df["ticker"].unique():
            tdf = df[df["ticker"] == ticker].sort_values("date")
            dates = tdf["date"].values

            # Calculate time deltas
            deltas = np.diff(dates).astype("timedelta64[h]").astype(float)

            # For hourly data, gaps > 18h on weekdays are suspicious
            # (market close ~16h + overnight = normal ~17h gap)
            # Weekend gaps (~65h) are normal
            suspicious_gaps = []
            for i, delta in enumerate(deltas):
                dt = pd.Timestamp(dates[i])
                next_dt = pd.Timestamp(dates[i + 1])
                # Skip weekends (Fri close to Mon open)
                if dt.weekday() == 4 and next_dt.weekday() == 0:
                    if delta > 80:  # More than ~3.3 days means missing data
                        suspicious_gaps.append({
                            "from": str(dates[i]),
                            "to": str(dates[i + 1]),
                            "hours": float(delta),
                            "type": "extended_weekend",
                        })
                elif delta > 24:  # More than 24h gap on non-weekend
                    suspicious_gaps.append({
                        "from": str(dates[i]),
                        "to": str(dates[i + 1]),
                        "hours": float(delta),
                        "type": "weekday_gap" if dt.weekday() < 4 else "weekend",
                    })

            gaps[ticker] = {
                "n_gaps": len(suspicious_gaps),
                "total_gap_hours": sum(g["hours"] for g in suspicious_gaps),
                "largest_gap_hours": max((g["hours"] for g in suspicious_gaps), default=0),
                "gaps": suspicious_gaps[:10],  # Top 10 only
            }

        return gaps

    def _check_ticker_coverage(self, watchlist_name: str = None) -> dict:
        """Check which tickers from watchlist are missing data."""
        result = {
            "loaded_tickers": sorted(self.price_df["ticker"].unique().tolist()),
            "n_loaded": self.price_df["ticker"].nunique(),
        }

        if watchlist_name and self.watchlist_path:
            try:
                import yaml
                with open(self.watchlist_path) as f:
                    watchlists = yaml.safe_load(f)
                if watchlist_name in watchlists:
                    expected = watchlists[watchlist_name].get("tickers", [])
                    loaded = set(result["loaded_tickers"])
                    missing = [t for t in expected if t not in loaded]
                    extra = [t for t in loaded if t not in expected]
                    result["watchlist"] = watchlist_name
                    result["expected_tickers"] = expected
                    result["missing_tickers"] = missing
                    result["extra_tickers"] = extra
                    result["coverage_pct"] = (
                        (len(expected) - len(missing)) / len(expected) * 100
                        if expected else 100
                    )
            except Exception as e:
                result["watchlist_error"] = str(e)

        return result

    def _check_data_quality(self) -> dict:
        """Check for null values, zeros, outliers."""
        df = self.price_df
        quality = {}

        for ticker in df["ticker"].unique():
            tdf = df[df["ticker"] == ticker]
            issues = []

            # Null checks
            null_counts = tdf[["open", "high", "low", "close", "volume"]].isnull().sum()
            for col, count in null_counts.items():
                if count > 0:
                    issues.append({"type": "null_values", "column": col, "count": int(count)})

            # Zero volume
            zero_vol = (tdf["volume"] == 0).sum()
            if zero_vol > 0:
                issues.append({"type": "zero_volume", "count": int(zero_vol),
                             "pct": float(zero_vol / len(tdf) * 100)})

            # Price outliers (> 3 std from rolling mean)
            close = tdf["close"]
            rolling_mean = close.rolling(20, min_periods=1).mean()
            rolling_std = close.rolling(20, min_periods=1).std()
            outliers = ((close - rolling_mean).abs() > 3 * rolling_std).sum()
            if outliers > 0:
                issues.append({"type": "price_outliers_3std", "count": int(outliers)})

            # Negative prices
            neg_prices = (tdf[["open", "high", "low", "close"]] < 0).any(axis=1).sum()
            if neg_prices > 0:
                issues.append({"type": "negative_prices", "count": int(neg_prices)})

            quality[ticker] = {
                "n_issues": len(issues),
                "issues": issues,
                "completeness_pct": float((1 - tdf.isnull().mean().mean()) * 100),
            }

        return quality

    def _check_resolution(self) -> dict:
        """Analyze data resolution and recommend higher-res options."""
        df = self.price_df
        sample = df[df["ticker"] == df["ticker"].iloc[0]].sort_values("date").head(100)
        deltas = np.diff(sample["date"].values).astype("timedelta64[m]").astype(float)

        # Filter to intraday deltas only (< 12 hours)
        intraday = deltas[deltas < 720]
        median_interval = float(np.median(intraday)) if len(intraday) > 0 else 0

        resolution_map = {
            (0, 3): "1m",
            (3, 8): "5m",
            (8, 20): "15m",
            (20, 40): "30m",
            (40, 90): "1h",
            (90, 300): "4h",
            (300, 1500): "1d",
        }

        detected = "unknown"
        for (lo, hi), label in resolution_map.items():
            if lo < median_interval <= hi:
                detected = label
                break

        return {
            "detected_interval": detected,
            "median_interval_minutes": round(median_interval, 1),
            "total_bars_per_ticker": int(len(sample)),
            "available_resolutions": {
                "current": detected,
                "higher_res_needed": ["5m", "15m"] if detected in ["1h", "4h", "1d"] else [],
                "data_source_for_higher_res": "Alpaca Markets (alpaca-py) — free, 7+ years of 1m/5m/15m data",
            },
            "bars_per_day_estimate": round(24 * 60 / median_interval, 1) if median_interval > 0 else 0,
        }

    def _check_benchmark_alignment(self) -> dict:
        """Check if benchmark data aligns with price data."""
        price_dates = set(self.price_df["date"].dt.date.unique())
        bench_dates = set(self.benchmark_df["date"].dt.date.unique())

        missing_in_bench = price_dates - bench_dates
        missing_in_price = bench_dates - price_dates

        return {
            "price_date_count": len(price_dates),
            "benchmark_date_count": len(bench_dates),
            "missing_in_benchmark": len(missing_in_bench),
            "missing_in_price": len(missing_in_price),
            "overlap_pct": float(
                len(price_dates & bench_dates) / max(len(price_dates), 1) * 100
            ),
            "benchmark_ticker": self.benchmark_df["ticker"].unique().tolist()
                if "ticker" in self.benchmark_df.columns else ["SPY"],
        }

    def _generate_recommendations(self, report: dict) -> list:
        """Generate actionable recommendations from gap analysis."""
        recs = []

        # Resolution
        res = report["resolution_analysis"]
        if res["detected_interval"] in ["1h", "4h", "1d"]:
            recs.append({
                "priority": "HIGH",
                "category": "data_resolution",
                "message": (
                    f"Current data is {res['detected_interval']}. "
                    "Higher resolution (5m/15m) via Alpaca Markets would enable "
                    "better intraday signal detection and more walk-forward windows."
                ),
                "action": "Install alpaca-py and run download with --interval 5m or 15m",
            })

        # Coverage
        cov = report["ticker_coverage"]
        if cov.get("missing_tickers"):
            recs.append({
                "priority": "HIGH",
                "category": "ticker_coverage",
                "message": (
                    f"Missing {len(cov['missing_tickers'])} tickers from watchlist: "
                    f"{', '.join(cov['missing_tickers'][:5])}..."
                ),
                "action": f"Run: python scripts/download_prices.py --watchlist {cov.get('watchlist', 'tech_giants')}",
            })

        # Data quality
        quality = report["data_quality"]
        bad_tickers = [t for t, q in quality.items() if q["n_issues"] > 2]
        if bad_tickers:
            recs.append({
                "priority": "MEDIUM",
                "category": "data_quality",
                "message": f"Tickers with quality issues: {', '.join(bad_tickers)}",
                "action": "Re-download affected tickers or add data cleaning step",
            })

        # Benchmark
        bench = report["benchmark_alignment"]
        if bench["overlap_pct"] < 95:
            recs.append({
                "priority": "MEDIUM",
                "category": "benchmark_alignment",
                "message": (
                    f"Benchmark-price date overlap is {bench['overlap_pct']:.1f}%. "
                    "Misaligned dates cause NaN in excess return calculations."
                ),
                "action": "Re-download benchmark data to match price date range",
            })

        # History depth
        summary = report["data_summary"]
        span = summary["date_range"]["span_days"]
        if span < 365:
            recs.append({
                "priority": "HIGH",
                "category": "history_depth",
                "message": (
                    f"Only {span} days of history. Need 2+ years for robust "
                    "walk-forward backtesting with statistical significance."
                ),
                "action": "Switch to daily data for longer history, or use Alpaca for deep intraday",
            })

        if not recs:
            recs.append({
                "priority": "INFO",
                "category": "general",
                "message": "Data looks good for regression testing.",
                "action": "Proceed with regression test run.",
            })

        return recs

    def _compute_quality_score(self, report: dict) -> dict:
        """Compute overall data quality score (0-100)."""
        score = 100

        # Deduct for missing tickers
        cov = report["ticker_coverage"]
        if cov.get("coverage_pct") is not None:
            score -= max(0, (100 - cov["coverage_pct"]) * 0.3)

        # Deduct for quality issues
        quality = report["data_quality"]
        total_issues = sum(q["n_issues"] for q in quality.values())
        score -= min(20, total_issues * 2)

        # Deduct for benchmark misalignment
        bench = report["benchmark_alignment"]
        score -= max(0, (100 - bench["overlap_pct"]) * 0.2)

        # Deduct for low resolution
        res = report["resolution_analysis"]
        if res["detected_interval"] in ["1d"]:
            score -= 15
        elif res["detected_interval"] in ["4h"]:
            score -= 10
        elif res["detected_interval"] in ["1h"]:
            score -= 5

        return {
            "score": round(max(0, min(100, score)), 1),
            "grade": (
                "A" if score >= 90 else
                "B" if score >= 80 else
                "C" if score >= 70 else
                "D" if score >= 60 else "F"
            ),
        }


# ── Multi-Resolution Runner ──────────────────────────────────────────────

class MultiResolutionRunner:
    """Run regression tests across multiple data resolutions."""

    RESOLUTION_CONFIGS = {
        "1d": {
            "train_years": 5.0,
            "test_years": 1.0,
            "step_days": 5.0,
            "rebalance_freq": "1d",
            "bars_per_day": 1,
        },
        "4h": {
            "train_years": 2.0,
            "test_years": 0.5,
            "step_days": 2.0,
            "rebalance_freq": "4h",
            "bars_per_day": 2,
        },
        "1h": {
            "train_years": 1.0,
            "test_years": 0.25,
            "step_days": 1.0,
            "rebalance_freq": "4h",
            "bars_per_day": 7,
        },
        "15m": {
            "train_years": 0.5,
            "test_years": 0.125,
            "step_days": 0.5,
            "rebalance_freq": "1h",
            "bars_per_day": 26,
        },
        "5m": {
            "train_years": 0.25,
            "test_years": 0.0625,
            "step_days": 0.25,
            "rebalance_freq": "30m",
            "bars_per_day": 78,
        },
    }

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path

    def run_resolution(
        self,
        resolution: str,
        watchlist: str = None,
        features: list = None,
        tune: bool = False,
        tuning_trials: int = 30,
        name: str = None,
    ) -> dict:
        """Run regression test for a specific resolution."""
        from src.config.config import load_config, BacktestConfig, ModelConfig
        from src.regression.feature_registry import FeatureRegistry, DEFAULT_BASELINE
        from src.regression.orchestrator import RegressionOrchestrator, RegressionTestConfig
        from src.regression.reporting import RegressionReporter

        config = load_config(self.config_path)

        # Override backtest config for this resolution
        res_config = self.RESOLUTION_CONFIGS.get(resolution, self.RESOLUTION_CONFIGS["1h"])
        config.backtest.train_years = res_config["train_years"]
        config.backtest.test_years = res_config["test_years"]
        config.backtest.step_days = res_config["step_days"]
        config.backtest.rebalance_freq = res_config["rebalance_freq"]

        # Load data
        from scripts.run_regression_test import load_data
        training_data, price_df, benchmark_df = load_data(config, watchlist)

        registry = FeatureRegistry()
        features_to_test = features or registry.get_default_order()

        reg_config = RegressionTestConfig(
            name=name or f"Regression {watchlist or 'default'} @ {resolution}",
            description=f"Automated regression test at {resolution} resolution",
            baseline_features=list(DEFAULT_BASELINE),
            features_to_test=features_to_test,
            tune_on_add=tune,
            tuning_trials=tuning_trials,
            objective_metric="mean_rank_ic",
            db_path="data/runs.db",
        )

        orchestrator = RegressionOrchestrator(
            config=reg_config,
            registry=registry,
            training_data=training_data,
            benchmark_data=benchmark_df,
            price_data=price_df,
            backtest_config=config.backtest,
            model_config=config.model,
        )

        results = orchestrator.run(verbose=True)

        # Generate reports
        output_dir = f"output/regression/{orchestrator.regression_id}"
        reporter = RegressionReporter(
            db=orchestrator.db,
            regression_id=orchestrator.regression_id,
        )
        report_paths = reporter.generate_all(output_dir)

        return {
            "regression_id": orchestrator.regression_id,
            "resolution": resolution,
            "output_dir": output_dir,
            "report_paths": report_paths,
            "n_steps": len(results),
            "final_sharpe": results[-1].metrics.get("sharpe_ratio", 0) if results else 0,
            "final_rank_ic": results[-1].metrics.get("mean_rank_ic", 0) if results else 0,
        }

    def run_all_resolutions(
        self,
        resolutions: list,
        watchlist: str = None,
        features: list = None,
        tune: bool = False,
    ) -> dict:
        """Run regression tests across all specified resolutions."""
        all_results = {}
        for res in resolutions:
            print(f"\n{'='*60}")
            print(f"  Running regression at {res} resolution")
            print(f"{'='*60}\n")
            try:
                result = self.run_resolution(
                    resolution=res,
                    watchlist=watchlist,
                    features=features,
                    tune=tune,
                    name=f"Auto Regression {watchlist or 'default'} @ {res}",
                )
                all_results[res] = result
            except Exception as e:
                logger.error(f"Failed at {res}: {e}")
                all_results[res] = {"error": str(e), "resolution": res}

        return all_results


# ── Report Generation ─────────────────────────────────────────────────────

def generate_gap_report(gap_analysis: dict, output_path: str) -> str:
    """Generate Markdown gap analysis report."""
    lines = []
    lines.append("# Data Gap Analysis Report")
    lines.append(f"\n**Generated**: {gap_analysis['timestamp']}")

    # Quality Score
    score = gap_analysis["overall_score"]
    lines.append(f"\n## Overall Data Quality: {score['grade']} ({score['score']}/100)\n")

    # Data Summary
    summary = gap_analysis["data_summary"]
    lines.append("## Data Summary\n")
    lines.append(f"| Property | Value |")
    lines.append(f"|----------|-------|")
    lines.append(f"| Total Rows | {summary['total_rows']:,} |")
    lines.append(f"| Tickers | {summary['n_tickers']} ({', '.join(summary['unique_tickers'])}) |")
    lines.append(f"| Date Range | {summary['date_range']['start']} to {summary['date_range']['end']} |")
    lines.append(f"| Span | {summary['date_range']['span_days']} days |")

    # Resolution
    res = gap_analysis["resolution_analysis"]
    lines.append(f"\n## Resolution Analysis\n")
    lines.append(f"| Property | Value |")
    lines.append(f"|----------|-------|")
    lines.append(f"| Detected Interval | {res['detected_interval']} |")
    lines.append(f"| Median Interval | {res['median_interval_minutes']} minutes |")
    lines.append(f"| Bars/Day | ~{res['bars_per_day_estimate']} |")
    if res["available_resolutions"]["higher_res_needed"]:
        lines.append(f"| Higher Res Needed | {', '.join(res['available_resolutions']['higher_res_needed'])} |")
        lines.append(f"| Recommended Source | {res['available_resolutions']['data_source_for_higher_res']} |")

    # Ticker Coverage
    cov = gap_analysis["ticker_coverage"]
    lines.append(f"\n## Ticker Coverage\n")
    lines.append(f"- **Loaded**: {cov['n_loaded']} tickers")
    if cov.get("watchlist"):
        lines.append(f"- **Watchlist**: {cov['watchlist']} ({len(cov.get('expected_tickers', []))} expected)")
        lines.append(f"- **Coverage**: {cov.get('coverage_pct', 100):.1f}%")
        if cov.get("missing_tickers"):
            lines.append(f"- **Missing**: {', '.join(cov['missing_tickers'])}")

    # Data Quality
    quality = gap_analysis["data_quality"]
    lines.append(f"\n## Data Quality per Ticker\n")
    lines.append(f"| Ticker | Issues | Completeness | Details |")
    lines.append(f"|--------|--------|-------------|---------|")
    for ticker, q in sorted(quality.items()):
        details = "; ".join(
            f"{i['type']}({i.get('count', '')})" for i in q["issues"]
        ) or "Clean"
        lines.append(f"| {ticker} | {q['n_issues']} | {q['completeness_pct']:.1f}% | {details} |")

    # Date Range Gaps
    date_gaps = gap_analysis["date_range_gaps"]
    total_gaps = sum(g["n_gaps"] for g in date_gaps.values())
    if total_gaps > 0:
        lines.append(f"\n## Date Range Gaps\n")
        lines.append(f"| Ticker | Suspicious Gaps | Largest Gap (hours) |")
        lines.append(f"|--------|----------------|---------------------|")
        for ticker, g in sorted(date_gaps.items()):
            if g["n_gaps"] > 0:
                lines.append(f"| {ticker} | {g['n_gaps']} | {g['largest_gap_hours']:.1f}h |")

    # Benchmark Alignment
    bench = gap_analysis["benchmark_alignment"]
    lines.append(f"\n## Benchmark Alignment\n")
    lines.append(f"| Property | Value |")
    lines.append(f"|----------|-------|")
    lines.append(f"| Price Dates | {bench['price_date_count']} |")
    lines.append(f"| Benchmark Dates | {bench['benchmark_date_count']} |")
    lines.append(f"| Overlap | {bench['overlap_pct']:.1f}% |")
    lines.append(f"| Missing in Benchmark | {bench['missing_in_benchmark']} dates |")

    # Recommendations
    lines.append(f"\n## Recommendations\n")
    for rec in gap_analysis["recommendations"]:
        icon = {"HIGH": "!!!", "MEDIUM": "!!", "INFO": "i"}.get(rec["priority"], "")
        lines.append(f"### [{rec['priority']}] {rec['category']}\n")
        lines.append(f"{rec['message']}\n")
        lines.append(f"**Action**: {rec['action']}\n")

    content = "\n".join(lines)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(content)

    return output_path


def generate_multi_resolution_report(results: dict, gap_analysis: dict, output_path: str) -> str:
    """Generate combined multi-resolution + gap analysis report."""
    lines = []
    lines.append("# Automated Regression Testing Report")
    lines.append(f"\n**Generated**: {datetime.now().isoformat()}")

    # Gap Analysis Summary
    score = gap_analysis["overall_score"]
    lines.append(f"\n## Data Quality Score: {score['grade']} ({score['score']}/100)")

    # Resolution Results
    lines.append(f"\n## Regression Results by Resolution\n")
    lines.append(f"| Resolution | Regression ID | Steps | Final Sharpe | Final Rank IC | Status |")
    lines.append(f"|-----------|---------------|-------|-------------|---------------|--------|")

    for res, result in sorted(results.items()):
        if "error" in result:
            lines.append(f"| {res} | - | - | - | - | FAILED: {result['error'][:40]} |")
        else:
            lines.append(
                f"| {res} | {result['regression_id'][:20]}... | {result['n_steps']} | "
                f"{result.get('final_sharpe', 0):.4f} | {result.get('final_rank_ic', 0):.4f} | OK |"
            )

    # Recommendations
    lines.append(f"\n## Next Steps\n")
    for rec in gap_analysis["recommendations"]:
        lines.append(f"- **[{rec['priority']}]** {rec['message']}")

    content = "\n".join(lines)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(content)

    return output_path


# ── Main CLI ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Automated Regression Testing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--watchlist", "-w", help="Watchlist name")
    parser.add_argument("--config", "-c", default="config/config.yaml", help="Config path")
    parser.add_argument("--resolutions", nargs="+", default=["1h"],
                       help="Data resolutions to test (default: 1h)")
    parser.add_argument("--features", nargs="+", help="Features to test")
    parser.add_argument("--tune", action="store_true", help="Enable parameter tuning")
    parser.add_argument("--tuning-trials", type=int, default=30, help="Trials per feature")
    parser.add_argument("--gap-analysis-only", action="store_true",
                       help="Only run gap analysis, no regression")
    parser.add_argument("--output-dir", default="output/automated",
                       help="Output directory (default: output/automated)")
    parser.add_argument("--name", "-n", help="Name for this run")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Gap Analysis ──
    print("\n" + "=" * 60)
    print("  Step 1: Data Gap Analysis")
    print("=" * 60 + "\n")

    watchlist_path = Path(__file__).parent.parent / "config" / "watchlists.yaml"
    analyzer = DataGapAnalyzer(
        price_path="data/prices.csv",
        benchmark_path="data/benchmark.csv",
        watchlist_path=str(watchlist_path),
    )
    gap_report = analyzer.run_full_analysis(watchlist_name=args.watchlist)

    # Save gap analysis
    gap_json_path = output_dir / "gap_analysis.json"
    with open(gap_json_path, "w") as f:
        json.dump(gap_report, f, indent=2, default=str)
    print(f"Gap analysis JSON: {gap_json_path}")

    gap_md_path = output_dir / "gap_analysis.md"
    generate_gap_report(gap_report, str(gap_md_path))
    print(f"Gap analysis report: {gap_md_path}")

    # Print summary
    score = gap_report["overall_score"]
    print(f"\nData Quality Score: {score['grade']} ({score['score']}/100)")
    for rec in gap_report["recommendations"]:
        print(f"  [{rec['priority']}] {rec['message']}")

    if args.gap_analysis_only:
        print("\nGap analysis complete. Skipping regression testing.")
        return

    # ── Step 2: Regression Testing ──
    print("\n" + "=" * 60)
    print("  Step 2: Regression Testing")
    print("=" * 60 + "\n")

    runner = MultiResolutionRunner(config_path=args.config)
    all_results = {}

    for resolution in args.resolutions:
        try:
            result = runner.run_resolution(
                resolution=resolution,
                watchlist=args.watchlist,
                features=args.features,
                tune=args.tune,
                tuning_trials=args.tuning_trials,
                name=args.name or f"Auto {args.watchlist or 'default'} @ {resolution}",
            )
            all_results[resolution] = result
            print(f"\n[{resolution}] Complete: Sharpe={result['final_sharpe']:.4f}, "
                  f"Rank IC={result['final_rank_ic']:.4f}")
        except Exception as e:
            logger.error(f"Failed at {resolution}: {e}", exc_info=True)
            all_results[resolution] = {"error": str(e), "resolution": resolution}

    # ── Step 3: Combined Report ──
    print("\n" + "=" * 60)
    print("  Step 3: Generating Combined Report")
    print("=" * 60 + "\n")

    combined_path = output_dir / "automated_regression_report.md"
    generate_multi_resolution_report(all_results, gap_report, str(combined_path))
    print(f"Combined report: {combined_path}")

    # Save results JSON
    results_json_path = output_dir / "regression_results.json"
    with open(results_json_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"Results JSON: {results_json_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
