"""Reporting for regression testing.

Generates JSON, Markdown, and CSV reports from regression test results.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from .database import RegressionDatabase


class RegressionReporter:
    """Generate reports from regression test results."""

    def __init__(self, db: RegressionDatabase, regression_id: str):
        self.db = db
        self.regression_id = regression_id

    def generate_all(self, output_dir: str) -> Dict[str, str]:
        """Generate all report formats. Returns dict of {format: path}."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        paths = {}
        paths["json"] = str(self.generate_summary_json(out / "regression_report.json"))
        paths["markdown"] = str(self.generate_markdown_report(out / "regression_report.md"))
        paths["csv"] = str(self.generate_csv_metrics(out / "regression_metrics.csv"))
        paths["leaderboard"] = str(self.generate_leaderboard_csv(out / "feature_leaderboard.csv"))

        # Tuned params
        steps = self.db.get_regression_steps(self.regression_id)
        tuned = {}
        for s in steps:
            if s.get("tuned_params_json"):
                tuned[s["feature_added"]] = json.loads(s["tuned_params_json"])
        if tuned:
            tp_path = out / "tuned_params.json"
            with open(tp_path, "w") as f:
                json.dump(tuned, f, indent=2)
            paths["tuned_params"] = str(tp_path)

        return paths

    def generate_summary_json(self, output_path: Path) -> Path:
        """Full structured JSON with all steps, metrics, significance."""
        test = self.db.get_regression_test(self.regression_id)
        steps = self.db.get_regression_steps(self.regression_id)
        leaderboard = self.db.get_feature_leaderboard(self.regression_id)

        report = {
            "regression_id": self.regression_id,
            "test": test,
            "steps": [],
            "leaderboard": leaderboard,
            "generated_at": datetime.now().isoformat(),
        }

        for s in steps:
            step_data = dict(s)
            # Parse JSON fields
            for json_field in [
                "metrics_json", "marginal_metrics_json", "significance_json",
                "feature_importance_json", "feature_set_json", "feature_columns_json",
                "window_ics_json", "window_rank_ics_json", "window_test_sharpes_json",
                "tuned_params_json", "model_config_json",
            ]:
                if step_data.get(json_field):
                    try:
                        step_data[json_field.replace("_json", "")] = json.loads(
                            step_data[json_field]
                        )
                    except (json.JSONDecodeError, TypeError):
                        pass
            report["steps"].append(step_data)

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        return output_path

    def generate_markdown_report(self, output_path: Path) -> Path:
        """Human-readable Markdown report with tables."""
        test = self.db.get_regression_test(self.regression_id)
        steps = self.db.get_regression_steps(self.regression_id)
        leaderboard = self.db.get_feature_leaderboard(self.regression_id)

        lines = []
        lines.append(f"# Regression Test Report: {test['name']}")
        lines.append(f"\n**ID**: {self.regression_id}")
        lines.append(f"**Date**: {test['created_at']}")
        lines.append(f"**Status**: {test['status']}")
        lines.append(f"**Duration**: {test.get('duration_seconds', 0):.1f}s")

        # Summary
        lines.append("\n## Summary\n")
        if steps:
            baseline = steps[0]
            final = steps[-1]
            lines.append(f"| Metric | Baseline | Final | Change |")
            lines.append(f"|--------|----------|-------|--------|")
            for m in ["sharpe_ratio", "mean_rank_ic", "excess_return", "hit_rate", "max_drawdown"]:
                b_val = baseline.get(m, 0) or 0
                f_val = final.get(m, 0) or 0
                delta = f_val - b_val
                lines.append(f"| {m} | {b_val:.4f} | {f_val:.4f} | {delta:+.4f} |")

        if test.get("best_feature"):
            lines.append(f"\n**Best Feature**: {test['best_feature']} "
                        f"(+{test.get('best_marginal_sharpe', 0):.4f} Sharpe)")

        # Step-by-Step Table
        lines.append("\n## Step-by-Step Results\n")
        lines.append("| Step | Feature | Sharpe | Rank IC | Marginal Sharpe | p-value | Sig? |")
        lines.append("|------|---------|--------|---------|-----------------|---------|------|")

        for s in steps:
            step = s["step_number"]
            feat = s["feature_added"]
            sharpe = s.get("sharpe_ratio", 0) or 0
            rank_ic = s.get("mean_rank_ic", 0) or 0
            m_sharpe = s.get("marginal_sharpe")
            m_sharpe_str = f"{m_sharpe:+.4f}" if m_sharpe is not None else "-"

            # Extract p-value from significance JSON
            p_val_str = "-"
            sig_str = "-"
            if s.get("significance_json"):
                try:
                    sig = json.loads(s["significance_json"])
                    if "rank_ic_paired_ttest" in sig:
                        p = sig["rank_ic_paired_ttest"].get("p_value", 1.0)
                        p_val_str = f"{p:.4f}"
                        sig_str = "YES" if p < 0.05 else "no"
                except (json.JSONDecodeError, TypeError):
                    pass

            lines.append(
                f"| {step} | {feat} | {sharpe:.4f} | {rank_ic:.4f} | "
                f"{m_sharpe_str} | {p_val_str} | {sig_str} |"
            )

        # Feature Leaderboard
        lines.append("\n## Feature Contribution Leaderboard\n")
        lines.append("| Rank | Feature | Marginal Sharpe | Marginal IC | Importance % | Significant? |")
        lines.append("|------|---------|-----------------|-------------|-------------|-------------|")

        for rank, feat in enumerate(leaderboard, 1):
            name = feat["feature_name"]
            ms = feat.get("marginal_sharpe", 0) or 0
            mi = feat.get("marginal_rank_ic", 0) or 0
            imp = (feat.get("feature_importance_pct", 0) or 0) * 100
            sig = "YES" if feat.get("is_significant") else "no"
            lines.append(f"| {rank} | {name} | {ms:+.4f} | {mi:+.4f} | {imp:.1f}% | {sig} |")

        # Guard Violations
        violations = []
        for s in steps:
            if s.get("metrics_json"):
                try:
                    metrics = json.loads(s["metrics_json"])
                    from .metrics import check_guard_metrics
                    viol = check_guard_metrics(metrics)
                    for v in viol:
                        v["step"] = s["step_number"]
                        v["feature"] = s["feature_added"]
                        violations.append(v)
                except Exception:
                    pass

        if violations:
            lines.append("\n## Guard Metric Violations\n")
            lines.append("| Step | Feature | Metric | Value | Threshold |")
            lines.append("|------|---------|--------|-------|-----------|")
            for v in violations:
                lines.append(
                    f"| {v['step']} | {v['feature']} | {v['metric']} | "
                    f"{v['value']:.4f} | {v['threshold']} |"
                )

        # Tuned Parameters
        has_tuned = any(s.get("tuned_params_json") for s in steps)
        if has_tuned:
            lines.append("\n## Tuned Parameters\n")
            for s in steps:
                if s.get("tuned_params_json"):
                    try:
                        params = json.loads(s["tuned_params_json"])
                        lines.append(f"**{s['feature_added']}**: {params}")
                    except Exception:
                        pass

        content = "\n".join(lines)
        with open(output_path, "w") as f:
            f.write(content)

        return output_path

    def generate_csv_metrics(self, output_path: Path) -> Path:
        """CSV with one row per step, all metrics as columns."""
        steps = self.db.get_regression_steps(self.regression_id)

        rows = []
        for s in steps:
            row = {
                "step": s["step_number"],
                "feature_added": s["feature_added"],
                "sharpe_ratio": s.get("sharpe_ratio"),
                "mean_rank_ic": s.get("mean_rank_ic"),
                "excess_return": s.get("excess_return"),
                "max_drawdown": s.get("max_drawdown"),
                "hit_rate": s.get("hit_rate"),
                "turnover": s.get("turnover"),
                "marginal_sharpe": s.get("marginal_sharpe"),
                "marginal_rank_ic": s.get("marginal_rank_ic"),
                "duration_seconds": s.get("duration_seconds"),
            }

            # Add extended metrics from JSON
            if s.get("metrics_json"):
                try:
                    metrics = json.loads(s["metrics_json"])
                    for k in ["ic_std", "ic_ir", "ic_pct_positive", "sortino_ratio",
                              "calmar_ratio", "train_test_sharpe_ratio", "volatility",
                              "total_return", "annualized_return"]:
                        if k in metrics:
                            row[k] = metrics[k]
                except Exception:
                    pass

            rows.append(row)

        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
        return output_path

    def generate_leaderboard_csv(self, output_path: Path) -> Path:
        """Features ranked by marginal contribution."""
        leaderboard = self.db.get_feature_leaderboard(self.regression_id)
        df = pd.DataFrame(leaderboard)
        if not df.empty:
            df.to_csv(output_path, index=False)
        else:
            pd.DataFrame(columns=[
                "feature_name", "marginal_sharpe", "marginal_rank_ic",
                "feature_importance_pct", "is_significant"
            ]).to_csv(output_path, index=False)
        return output_path

    def get_cumulative_progress_data(self) -> pd.DataFrame:
        """DataFrame for plotting cumulative performance as features are added."""
        steps = self.db.get_regression_steps(self.regression_id)
        rows = []
        for s in steps:
            rows.append({
                "step": s["step_number"],
                "feature_added": s["feature_added"],
                "sharpe_ratio": s.get("sharpe_ratio", 0),
                "mean_rank_ic": s.get("mean_rank_ic", 0),
                "excess_return": s.get("excess_return", 0),
                "hit_rate": s.get("hit_rate", 0),
                "max_drawdown": s.get("max_drawdown", 0),
            })
        return pd.DataFrame(rows)
