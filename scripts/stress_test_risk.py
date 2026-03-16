#!/usr/bin/env python3
"""Stress test the RiskManager with simulated market crash scenarios.

Tests drawdown-from-peak close, daily loss halt, and concentration cap
against historical crash patterns.

Usage:
    python scripts/stress_test_risk.py
"""

import json
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np


# Import RiskManager from paper trading
from scripts.paper_trading import RiskManager


def simulate_scenario(name: str, description: str,
                      daily_returns: List[float],
                      risk_manager: RiskManager,
                      initial_value: float = 100000.0) -> Dict:
    """Simulate a market scenario through the risk manager.

    Returns detailed results including when each rule triggered.
    """
    portfolio_value = initial_value
    peak_value = initial_value
    events = []
    halted = False
    halted_day = None
    liquidated = False
    liquidated_day = None

    values = [initial_value]
    peaks = [initial_value]

    for day, ret in enumerate(daily_returns, 1):
        if halted or liquidated:
            # After halt/liquidation, hold cash
            values.append(portfolio_value)
            peaks.append(peak_value)
            continue

        # Apply daily return
        prev_value = portfolio_value
        portfolio_value *= (1 + ret)
        peak_value = max(peak_value, portfolio_value)
        values.append(portfolio_value)
        peaks.append(peak_value)

        daily_pnl = (portfolio_value / prev_value) - 1
        cumulative_return = (portfolio_value / initial_value) - 1
        drawdown_from_peak = (peak_value - portfolio_value) / peak_value if peak_value > 0 else 0

        # Check daily loss limit
        dl_event = risk_manager.check_daily_loss(daily_pnl)
        if dl_event:
            events.append({
                "day": day,
                "type": "daily_loss_halt",
                "detail": dl_event,
                "daily_return": daily_pnl,
                "portfolio_value": portfolio_value,
                "cumulative_return": cumulative_return,
            })
            halted = True
            halted_day = day

        # Check drawdown from peak
        dd_event = risk_manager.check_drawdown(portfolio_value, peak_value, initial_value)
        if dd_event:
            events.append({
                "day": day,
                "type": "drawdown_close",
                "detail": dd_event,
                "drawdown": drawdown_from_peak,
                "portfolio_value": portfolio_value,
                "peak_value": peak_value,
                "cumulative_return": cumulative_return,
            })
            liquidated = True
            liquidated_day = day

    final_value = portfolio_value
    max_drawdown = min((np.array(values) / np.maximum.accumulate(values)) - 1)
    total_return = (final_value / initial_value) - 1

    return {
        "scenario": name,
        "description": description,
        "days": len(daily_returns),
        "initial_value": initial_value,
        "final_value": final_value,
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "peak_value": max(values),
        "halted": halted,
        "halted_day": halted_day,
        "liquidated": liquidated,
        "liquidated_day": liquidated_day,
        "risk_events": events,
        "saved_by_risk_rules": halted or liquidated,
        "value_at_exit": portfolio_value,
        "value_without_rules": initial_value * np.prod([1 + r for r in daily_returns]),
        "loss_prevented": (initial_value * np.prod([1 + r for r in daily_returns])) - portfolio_value
            if (halted or liquidated) else 0,
    }


def main():
    rm = RiskManager(
        drawdown_pct=0.30,
        min_profit_pct=0.05,
        daily_loss_limit=-0.05,
        max_position_weight=0.25,
    )

    print("=" * 70)
    print("RISK MANAGER STRESS TEST")
    print("=" * 70)
    print(f"\nRules: drawdown_close={rm.drawdown_pct:.0%} (after {rm.min_profit_pct:.0%} profit), "
          f"daily_loss={rm.daily_loss_limit:.0%}, concentration={rm.max_position_weight:.0%}")

    scenarios = []

    # --- Scenario 1: 2020 COVID Crash ---
    # S&P 500 dropped ~34% in 23 trading days (Feb 19 - Mar 23, 2020)
    # But first gained ~5% in Jan-Feb
    covid_returns = (
        [0.003] * 20 +  # +6% run-up over 4 weeks
        [-0.005] * 3 +  # mild decline
        [-0.03, -0.04, -0.03, -0.028, -0.05, -0.03, -0.02, -0.04,
         -0.01, -0.05, -0.04, -0.028, -0.12, -0.06, -0.05, -0.03,
         -0.03, -0.029, -0.04, -0.028] +  # crash phase
        [0.04, 0.06, 0.03, 0.05, 0.02] +  # recovery
        [0.01] * 10  # continued recovery
    )
    scenarios.append(simulate_scenario(
        "COVID Crash (2020)",
        "Portfolio gains 6% then crashes 34% in 23 days, followed by V-shaped recovery",
        covid_returns, rm,
    ))

    # --- Scenario 2: 2022 Tech Bear ---
    # Nasdaq dropped ~33% over 9 months (Jan-Sep 2022)
    # Slow grind down with occasional bounces
    np.random.seed(42)
    tech_bear = []
    for week in range(40):  # 40 weeks
        if week < 5:
            # Initial small gains
            tech_bear.extend(np.random.normal(0.001, 0.008, 5).tolist())
        else:
            # Slow bleed with occasional relief rallies
            if week % 6 == 0:
                tech_bear.extend(np.random.normal(0.008, 0.01, 5).tolist())  # relief rally
            else:
                tech_bear.extend(np.random.normal(-0.004, 0.012, 5).tolist())  # bleed
    scenarios.append(simulate_scenario(
        "Tech Bear Market (2022)",
        "Slow 33% decline over 9 months with periodic relief rallies",
        tech_bear, rm,
    ))

    # --- Scenario 3: Flash Crash ---
    # Single day -10% drop (like Oct 2008 or flash crash events)
    flash_crash = (
        [0.005] * 30 +  # +15% over 6 weeks (builds up profit)
        [-0.10] +        # flash crash: -10% in one day
        [0.03, 0.02, 0.01, -0.01, 0.02] +  # recovery
        [0.005] * 10  # continued
    )
    scenarios.append(simulate_scenario(
        "Flash Crash (-10% single day)",
        "Portfolio gains 15% then suffers single-day -10% crash",
        flash_crash, rm,
    ))

    # --- Scenario 4: Slow Bleed ---
    # -20% over 3 months, no single big day
    np.random.seed(123)
    slow_bleed = (
        [0.004] * 15 +  # +6% build-up
        np.random.normal(-0.003, 0.005, 60).tolist()  # slow bleed ~-18% over 3 months
    )
    scenarios.append(simulate_scenario(
        "Slow Bleed (-20% over 3 months)",
        "Portfolio gains 6% then slowly bleeds -20% with no large single-day drops",
        slow_bleed, rm,
    ))

    # --- Scenario 5: V-Recovery (tests no false triggers) ---
    # Drop 15% then recover fully — risk rules should NOT trigger
    v_recovery = (
        [0.002] * 10 +   # +2% build-up (not enough for drawdown rule)
        [-0.02] * 8 +     # -15% decline
        [0.025] * 8 +     # full recovery
        [0.003] * 10      # continued gains
    )
    scenarios.append(simulate_scenario(
        "V-Recovery (no profit, no trigger)",
        "Drop 15% without prior profit — drawdown rule should NOT trigger",
        v_recovery, rm,
    ))

    # --- Scenario 6: Bull then Crash (worst case for drawdown rule) ---
    # Gain 30% then crash 40%
    bull_crash = (
        [0.005] * 50 +   # +28% over 10 weeks
        [-0.05, -0.06, -0.04, -0.05, -0.03, -0.04, -0.06, -0.03,
         -0.05, -0.04, -0.03, -0.05, -0.02, -0.04, -0.03]  # -55% crash
    )
    scenarios.append(simulate_scenario(
        "Bull then Crash (+28% then -55%)",
        "Strong bull run builds profit, then severe crash tests drawdown-from-peak rule",
        bull_crash, rm,
    ))

    # --- Concentration Cap Test ---
    print("\n" + "=" * 70)
    print("CONCENTRATION CAP TEST")
    print("=" * 70)

    test_cases = [
        {"NVDA": 0.40, "AAPL": 0.30, "MSFT": 0.30},
        {"NVDA": 0.50, "AAPL": 0.25, "MSFT": 0.15, "GOOGL": 0.10},
        {"NVDA": 0.20, "AAPL": 0.20, "MSFT": 0.20, "GOOGL": 0.20, "META": 0.20},
    ]

    for weights in test_cases:
        capped = rm.apply_concentration_cap(weights)
        print(f"\n  Input:  {', '.join(f'{t}:{w:.0%}' for t, w in weights.items())}")
        print(f"  Output: {', '.join(f'{t}:{w:.0%}' for t, w in capped.items())}")
        violations = [t for t, w in weights.items() if w > rm.max_position_weight]
        if violations:
            print(f"  Capped: {violations} (was > {rm.max_position_weight:.0%})")
        else:
            print(f"  No changes needed")

    # --- Summary ---
    print("\n" + "=" * 70)
    print("SCENARIO RESULTS SUMMARY")
    print("=" * 70)

    print(f"\n{'Scenario':<35} {'Days':>5} {'Return':>8} {'MaxDD':>8} {'Halted':>7} "
          f"{'Liquidated':>11} {'Day':>5} {'Saved':>12}")
    print("-" * 100)

    for s in scenarios:
        exit_day = s["halted_day"] or s["liquidated_day"] or "-"
        saved = f"${s['loss_prevented']:+,.0f}" if s["loss_prevented"] != 0 else "-"
        print(f"{s['scenario']:<35} {s['days']:>5} {s['total_return']:>+7.1%} "
              f"{s['max_drawdown']:>+7.1%} {'YES' if s['halted'] else 'no':>7} "
              f"{'YES' if s['liquidated'] else 'no':>11} {str(exit_day):>5} {saved:>12}")

    print("\n" + "-" * 100)
    triggered = sum(1 for s in scenarios if s["saved_by_risk_rules"])
    false_neg = sum(1 for s in scenarios if not s["saved_by_risk_rules"]
                    and s["total_return"] < -0.20)
    print(f"Risk rules triggered: {triggered}/{len(scenarios)} scenarios")
    print(f"False negatives (>20% loss, no trigger): {false_neg}")

    # Detail events
    for s in scenarios:
        if s["risk_events"]:
            print(f"\n  {s['scenario']}:")
            for e in s["risk_events"]:
                print(f"    Day {e['day']}: {e['type']} — {e['detail']}")
            if s["loss_prevented"] != 0:
                print(f"    Without rules: ${s['value_without_rules']:,.0f} "
                      f"({(s['value_without_rules']/s['initial_value'])-1:+.1%})")
                print(f"    With rules:    ${s['value_at_exit']:,.0f} "
                      f"({(s['value_at_exit']/s['initial_value'])-1:+.1%})")
                print(f"    Loss prevented: ${s['loss_prevented']:,.0f}")

    # Save report
    report_path = Path("output/reports/stress_test_risk_manager.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(scenarios, f, indent=2, default=str)
    print(f"\nReport saved: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
