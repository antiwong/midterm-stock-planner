from src.api.db import cached_response
"""Watchlist Comparison router."""

import time
import logging
from fastapi import APIRouter, Query

from src.data.shared_db import (
    WATCHLISTS,
    get_active_watchlists,
    load_regression_results,
    load_ensemble_comparison,
    load_stress_test,
    load_watchlist_config,
    load_ticker_configs,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/comparison", tags=["comparison"])

# LLM commentary cache
_cache: dict[str, tuple[float, str]] = {}
CACHE_TTL = 3600 * 6


@router.get("/regression")
@cached_response(ttl=300)
def get_regression():
    """Regression results across all watchlists."""
    results = load_regression_results()
    if not results:
        return {"error": "No regression results found.", "results": {}}

    summary = []
    for wl, data in results.items():
        test = data.get("test", {})
        steps = data.get("steps", [])
        baseline_sharpe = steps[0].get("sharpe_ratio", 0) if steps else 0
        summary.append({
            "watchlist": wl,
            "baseline_sharpe": baseline_sharpe,
            "peak_sharpe": max((s.get("sharpe_ratio", 0) or 0) for s in steps) if steps else 0,
            "final_sharpe": test.get("final_sharpe", 0),
            "final_ic": test.get("final_rank_ic", 0),
            "best_feature": test.get("best_feature", "?"),
            "best_delta": test.get("best_marginal_sharpe", 0),
            "duration_min": round(test.get("duration_seconds", 0) / 60, 1),
        })

    # Feature impact data for heatmap
    feature_data = {}
    for wl, data in results.items():
        for step in data.get("steps", []):
            feature = step.get("feature_added", "")
            if feature and feature != "BASELINE":
                delta = step.get("marginal_sharpe", 0) or 0
                if feature not in feature_data:
                    feature_data[feature] = {}
                feature_data[feature][wl] = delta

    return {
        "summary": summary,
        "feature_impact": feature_data,
    }


@router.get("/ensemble")
@cached_response(ttl=300)
def get_ensemble():
    """Ensemble vs ML-only comparison."""
    data = load_ensemble_comparison()
    if data is None:
        return {"error": "No ensemble comparison found."}
    return data


@router.get("/stress-test")
@cached_response(ttl=300)
def get_stress_test():
    """Stress test results."""
    data = load_stress_test()
    if data is None:
        return {"error": "No stress test results found."}
    return {"scenarios": data}


@router.get("/coverage")
@cached_response(ttl=300)
def get_coverage():
    """Per-ticker optimization coverage across watchlists."""
    wl_config = load_watchlist_config()
    configs = load_ticker_configs()

    coverage = []
    for name in get_active_watchlists():
        wl = wl_config.get(name, {})
        symbols = wl.get("symbols", [])
        with_config = sum(1 for s in symbols if s in configs)
        coverage.append({
            "watchlist": name,
            "total_tickers": len(symbols),
            "with_config": with_config,
            "coverage_pct": round(with_config / len(symbols) * 100, 1) if symbols else 0,
        })

    return {"coverage": coverage}


def _call_llm(prompt: str) -> str:
    """Call Gemini (preferred) or OpenAI as fallback."""
    from src.config.api_keys import get_api_key

    google_key = get_api_key("GOOGLE_API_KEY")
    if google_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=google_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            return response.text or "No commentary generated."
        except Exception as e:
            logger.warning(f"Gemini failed, falling back to OpenAI: {e}")

    openai_key = get_api_key("OPENAI_API_KEY")
    if openai_key:
        import openai
        client = openai.OpenAI(api_key=openai_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.3,
        )
        return response.choices[0].message.content or "No commentary generated."

    raise RuntimeError("No LLM API key configured (GOOGLE_API_KEY or OPENAI_API_KEY)")


@router.get("/commentary")
@cached_response(ttl=300)
def get_commentary(regenerate: bool = Query(False)):
    """LLM-generated commentary on watchlist comparison results."""
    cache_key = "comparison_commentary"

    if not regenerate and cache_key in _cache:
        ts, text = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return {"commentary": text, "cached": True}

    # Gather all comparison data
    regression = load_regression_results()
    ensemble = load_ensemble_comparison()
    stress = load_stress_test()
    wl_config = load_watchlist_config()
    configs = load_ticker_configs()

    lines = [
        "You are a quantitative analyst reviewing a watchlist comparison dashboard for a stock prediction system.",
        "The system runs ML models on multiple watchlists (portfolios) and compares their performance.",
        "Below is a summary of all available comparison data. Write a concise analyst note.",
        "",
    ]

    # Regression data
    if regression:
        lines.append("## Regression Test Results")
        for wl, data in regression.items():
            test = data.get("test", {})
            steps = data.get("steps", [])
            baseline = steps[0].get("sharpe_ratio", 0) if steps else 0
            peak = max((s.get("sharpe_ratio", 0) or 0) for s in steps) if steps else 0
            lines.append(f"  - {wl}: baseline Sharpe {baseline:.3f}, peak {peak:.3f}, final {test.get('final_sharpe', 0):.3f}, "
                         f"IC {test.get('final_rank_ic', 0):.4f}, best feature: {test.get('best_feature', '?')} (+{test.get('best_marginal_sharpe', 0):.3f})")
        lines.append("")

    # Ensemble data
    if ensemble and not isinstance(ensemble, dict) or (isinstance(ensemble, dict) and "error" not in ensemble):
        if isinstance(ensemble, dict):
            ml = ensemble.get("ml_metrics", {})
            ens = ensemble.get("ensemble_metrics", {})
            lines.append("## Ensemble vs ML-Only")
            lines.append(f"  - ML-Only: Sharpe {ml.get('sharpe', 0):.3f}, return {ml.get('total_return', 0)*100:.1f}%, max DD {ml.get('max_drawdown', 0)*100:.1f}%, win rate {ml.get('win_rate', 0)*100:.1f}%")
            lines.append(f"  - Ensemble: Sharpe {ens.get('sharpe', 0):.3f}, return {ens.get('total_return', 0)*100:.1f}%, max DD {ens.get('max_drawdown', 0)*100:.1f}%, win rate {ens.get('win_rate', 0)*100:.1f}%")
            lines.append(f"  - Verdict: {ensemble.get('verdict', 'N/A')}")
            lines.append("")

    # Stress test data
    if stress:
        lines.append("## Stress Test Scenarios")
        for s in stress:
            lines.append(f"  - {s.get('scenario', '?')}: return {s.get('total_return', 0)*100:.1f}%, max DD {s.get('max_drawdown', 0)*100:.1f}%, "
                         f"halted: {'YES' if s.get('halted') else 'NO'}, "
                         f"with rules ${s.get('value_at_exit', 0):,.0f} vs without ${s.get('value_without_rules', 0):,.0f}")
        lines.append("")

    # Coverage data
    lines.append("## Per-Ticker Optimization Coverage")
    for name in get_active_watchlists():
        wl = wl_config.get(name, {})
        symbols = wl.get("symbols", [])
        with_config = sum(1 for s in symbols if s in configs)
        pct = round(with_config / len(symbols) * 100, 1) if symbols else 0
        lines.append(f"  - {name}: {with_config}/{len(symbols)} tickers ({pct}%)")
    lines.append("")

    if len(lines) <= 6:
        return {"commentary": "No comparison data available yet. Run the analysis pipeline first.", "cached": False}

    lines.append("Write a concise analyst commentary (3-5 short paragraphs) covering:")
    lines.append("1. Which watchlist has the strongest ML signal (best Sharpe, IC) and which is weakest")
    lines.append("2. Whether the ensemble approach adds value over ML-only")
    lines.append("3. How the risk manager performs under stress — does it protect capital?")
    lines.append("4. Feature importance patterns — which features drive returns across watchlists?")
    lines.append("5. Coverage gaps and one actionable recommendation")
    lines.append("")
    lines.append("Be direct and specific. Use numbers. No fluff. Write like a Bloomberg terminal note.")

    prompt = "\n".join(lines)

    try:
        text = _call_llm(prompt)
    except Exception as e:
        logger.error(f"LLM commentary failed: {e}")
        return {"commentary": f"Commentary generation failed: {str(e)}", "cached": False}

    _cache[cache_key] = (time.time(), text)
    return {"commentary": text, "cached": False}
