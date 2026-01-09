"""
Gemini Commentary Module
========================
Provides optional AI-generated commentary for portfolio analysis.

IMPORTANT: Gemini is used ONLY for explanation and critique, NOT for decision-making.
All portfolio construction, stock selection, and weighting is done numerically
through the domain_analysis module and backtest pipeline.

Gemini's role:
- Explain patterns in the numeric data
- Highlight concentration risks or style tilts
- Compare portfolios in plain language
- Generate natural-language summaries for reports

Gemini is explicitly instructed NOT to:
- Change tickers or weights
- Make buy/sell recommendations
- Override numeric analysis
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

import pandas as pd


def get_gemini_client():
    """Get Gemini client if available."""
    try:
        import google.generativeai as genai
        
        api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            return None
        
        genai.configure(api_key=api_key)
        
        # Try different model names in order of preference
        model_names = [
            'gemini-2.0-flash-exp',
            'gemini-1.5-flash-latest', 
            'gemini-1.5-pro-latest',
            'gemini-pro',
        ]
        
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(model_name)
                # Quick test to see if model is accessible
                return model
            except Exception:
                continue
        
        # Fallback to default
        return genai.GenerativeModel('gemini-pro')
    except ImportError:
        return None
    except Exception:
        return None


SYSTEM_PROMPT = """You are a portfolio analysis assistant providing commentary on quantitative stock analysis.

IMPORTANT CONSTRAINTS:
- You are in READ-ONLY mode: Do NOT suggest changing any tickers, weights, or allocations
- All portfolio decisions have already been made numerically - your role is to EXPLAIN and CRITIQUE
- Focus on identifying patterns, risks, and characteristics visible in the data
- Be specific and reference actual numbers from the provided data

Your commentary should:
1. Explain what the numbers reveal about the portfolio's characteristics
2. Highlight any concentration risks (sector, factor, or individual stock)
3. Identify style tilts (growth vs value, high vs low beta, etc.)
4. Note any notable patterns in the quality/value scores
5. Provide context that helps interpret the risk metrics

Do NOT:
- Suggest adding or removing specific stocks
- Recommend changing weights or allocations
- Make forward-looking return predictions
- Override or contradict the quantitative analysis
"""


def generate_portfolio_commentary(
    portfolio_df: pd.DataFrame,
    metrics: Dict[str, float],
    sector_breakdown: Optional[pd.DataFrame] = None,
) -> Optional[str]:
    """
    Generate natural-language commentary for a portfolio.
    
    Args:
        portfolio_df: DataFrame with holdings (ticker, weight, scores)
        metrics: Dictionary of risk metrics
        sector_breakdown: Optional sector-level aggregations
    
    Returns:
        Commentary string or None if Gemini unavailable
    """
    client = get_gemini_client()
    if client is None:
        return None
    
    # Prepare data summary for Gemini
    data_summary = _prepare_portfolio_summary(portfolio_df, metrics, sector_breakdown)
    
    prompt = f"""{SYSTEM_PROMPT}

Please provide commentary on the following portfolio:

{data_summary}

Provide a structured commentary with these sections:
1. **Portfolio Overview**: What type of portfolio is this? (style, sector focus)
2. **Concentration Analysis**: Any concentration risks visible in the data?
3. **Quality-Value Assessment**: What do the scores tell us about the holdings?
4. **Risk Profile**: Interpretation of the risk metrics
5. **Key Observations**: 2-3 notable patterns or characteristics

Remember: Do NOT suggest changing any holdings or weights. Only explain what the numbers show."""

    try:
        response = client.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Commentary generation failed: {str(e)}"


def generate_comparison_commentary(
    portfolio1: pd.DataFrame,
    portfolio2: pd.DataFrame,
    metrics1: Dict[str, float],
    metrics2: Dict[str, float],
    labels: tuple = ("Portfolio A", "Portfolio B"),
) -> Optional[str]:
    """
    Generate commentary comparing two portfolios.
    
    Args:
        portfolio1, portfolio2: DataFrames with holdings
        metrics1, metrics2: Risk metrics for each
        labels: Names for the portfolios
    
    Returns:
        Comparison commentary or None
    """
    client = get_gemini_client()
    if client is None:
        return None
    
    summary1 = _prepare_portfolio_summary(portfolio1, metrics1)
    summary2 = _prepare_portfolio_summary(portfolio2, metrics2)
    
    prompt = f"""{SYSTEM_PROMPT}

Please compare these two portfolios:

=== {labels[0]} ===
{summary1}

=== {labels[1]} ===
{summary2}

Provide a structured comparison:
1. **Key Differences**: How do the portfolios differ in composition?
2. **Risk Comparison**: Which has better/worse risk metrics and why?
3. **Style Differences**: Any notable differences in style tilts?
4. **Diversification**: Which is more/less diversified?
5. **Trade-offs**: What is each portfolio optimizing for?

Remember: Do NOT recommend one over the other or suggest changes. Only explain the differences."""

    try:
        response = client.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Comparison failed: {str(e)}"


def generate_risk_commentary(
    metrics: Dict[str, float],
    holdings_count: int,
    sector_weights: Optional[Dict[str, float]] = None,
) -> Optional[str]:
    """
    Generate commentary focused on risk characteristics.
    
    Args:
        metrics: Risk metrics dictionary
        holdings_count: Number of holdings
        sector_weights: Optional sector weight breakdown
    
    Returns:
        Risk commentary or None
    """
    client = get_gemini_client()
    if client is None:
        return None
    
    risk_summary = f"""
Portfolio Risk Profile:
- Number of holdings: {holdings_count}
- Volatility: {metrics.get('volatility', 'N/A'):.2%}
- Sharpe Ratio: {metrics.get('sharpe_ratio', 'N/A'):.2f}
- Sortino Ratio: {metrics.get('sortino_ratio', 'N/A'):.2f}
- Max Drawdown: {metrics.get('max_drawdown', 'N/A'):.2%}
- VaR (95%): {metrics.get('var_95', 'N/A'):.2%}
- CVaR (95%): {metrics.get('cvar_95', 'N/A'):.2%}
- Diversification Score: {metrics.get('diversification_score', 'N/A'):.3f}
- Effective N: {metrics.get('effective_n', 'N/A'):.1f}
"""

    if sector_weights:
        risk_summary += "\nSector Weights:\n"
        for sector, weight in sorted(sector_weights.items(), key=lambda x: -x[1]):
            risk_summary += f"  - {sector}: {weight:.1%}\n"
    
    prompt = f"""{SYSTEM_PROMPT}

Analyze and explain the risk profile of this portfolio:

{risk_summary}

Provide:
1. **Overall Risk Assessment**: Is this a conservative, moderate, or aggressive portfolio?
2. **Risk Metric Interpretation**: What do these specific numbers tell us?
3. **Concentration Risk**: Based on effective N and sector weights
4. **Tail Risk**: Based on VaR/CVaR
5. **Considerations**: What should an investor understand about this risk profile?

Remember: Only explain the numbers, do NOT suggest reducing/increasing risk."""

    try:
        response = client.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Risk commentary failed: {str(e)}"


def _prepare_portfolio_summary(
    portfolio_df: pd.DataFrame,
    metrics: Dict[str, float],
    sector_breakdown: Optional[pd.DataFrame] = None,
) -> str:
    """Prepare a text summary of portfolio data for Gemini."""
    
    summary_parts = []
    
    # Holdings summary
    summary_parts.append("=== Holdings ===")
    cols_to_show = ['ticker', 'sector', 'weight', 'domain_score', 'value_score', 
                    'quality_score', 'model_score', 'pe_ratio', 'roe']
    available_cols = [c for c in cols_to_show if c in portfolio_df.columns]
    
    if len(portfolio_df) > 0:
        for _, row in portfolio_df.head(15).iterrows():
            parts = []
            for col in available_cols:
                val = row.get(col)
                if col == 'weight' and val is not None:
                    parts.append(f"{col}={val:.1%}")
                elif col in ['domain_score', 'value_score', 'quality_score', 'model_score']:
                    if val is not None:
                        parts.append(f"{col}={val:.1f}")
                elif col == 'pe_ratio' and val is not None:
                    parts.append(f"PE={val:.1f}")
                elif col == 'roe' and val is not None:
                    parts.append(f"ROE={val:.1%}")
                elif val is not None:
                    parts.append(f"{col}={val}")
            summary_parts.append(f"  {', '.join(parts)}")
    
    # Risk metrics
    summary_parts.append("\n=== Risk Metrics ===")
    for key, val in metrics.items():
        if isinstance(val, float):
            if 'ratio' in key.lower():
                summary_parts.append(f"  {key}: {val:.2f}")
            elif 'score' in key.lower() or key == 'effective_n':
                summary_parts.append(f"  {key}: {val:.2f}")
            else:
                summary_parts.append(f"  {key}: {val:.2%}")
    
    # Sector breakdown
    if sector_breakdown is not None and len(sector_breakdown) > 0:
        summary_parts.append("\n=== Sector Breakdown ===")
        for sector, row in sector_breakdown.iterrows():
            weight = row.get('equal_weight', row.get('weight', 0))
            count = row.get('count', 0)
            summary_parts.append(f"  {sector}: {weight:.1%} ({count} stocks)")
    
    return "\n".join(summary_parts)


RECOMMENDATION_PROMPT = """You are a portfolio advisor providing investment recommendations based on quantitative analysis.

You will receive:
1. Vertical analysis: Top candidates from each sector ranked by domain score (model + value + quality)
2. Horizontal analysis: Cross-sector portfolio construction with risk metrics
3. Historical backtest performance

Your task is to create THREE portfolio recommendations for different investor profiles:

1. **CONSERVATIVE** (Low Risk)
   - Target: Capital preservation with modest growth
   - Max volatility: ~15% annualized
   - Time horizon: 1-3 years
   - Focus: High quality, low beta, defensive sectors

2. **BALANCED** (Moderate Risk)
   - Target: Growth with reasonable risk management
   - Max volatility: ~20% annualized  
   - Time horizon: 3-5 years
   - Focus: Mix of growth and value

3. **AGGRESSIVE** (High Risk)
   - Target: Maximum growth, accept higher drawdowns
   - Max volatility: ~30%+ annualized
   - Time horizon: 5+ years
   - Focus: High momentum, growth stocks

For each recommendation, provide:
- Suggested allocation (top 5-10 stocks from the candidates)
- Suggested weights (must sum to 100%)
- Expected return range (low/mid/high scenarios)
- Risk assessment (volatility, max drawdown estimate)
- Key risks to monitor
- Rebalancing frequency suggestion

IMPORTANT: Base your recommendations ONLY on the stocks provided in the analysis data.
Use the domain scores, sector breakdown, and risk metrics to justify your allocations.
"""


def generate_portfolio_recommendations(
    vertical_results: Dict[str, Any],
    horizontal_result: Dict[str, Any],
    backtest_metrics: Dict[str, float],
    all_candidates: pd.DataFrame,
) -> Optional[Dict[str, Any]]:
    """
    Generate portfolio recommendations for different risk profiles.
    
    Uses vertical (within-sector) and horizontal (cross-sector) analysis
    to create Conservative, Balanced, and Aggressive portfolios.
    
    Args:
        vertical_results: Results from vertical analysis by sector
        horizontal_result: Results from horizontal portfolio construction
        backtest_metrics: Historical backtest performance metrics
        all_candidates: DataFrame with all stock candidates and scores
    
    Returns:
        Dictionary with recommendations for each profile, or None if failed
    """
    client = get_gemini_client()
    if client is None:
        return None
    
    # Prepare vertical analysis summary
    vertical_summary = "=== VERTICAL ANALYSIS (Top Candidates by Sector) ===\n"
    if isinstance(vertical_results, dict):
        for sector, result in vertical_results.items():
            if hasattr(result, 'candidates') and len(result.candidates) > 0:
                vertical_summary += f"\n{sector}:\n"
                for _, row in result.candidates.head(5).iterrows():
                    ticker = row.get('ticker', 'N/A')
                    domain_score = row.get('domain_score', 0)
                    value_score = row.get('value_score', 0)
                    quality_score = row.get('quality_score', 0)
                    vertical_summary += f"  - {ticker}: domain={domain_score:.1f}, value={value_score:.1f}, quality={quality_score:.1f}\n"
    
    # Prepare horizontal analysis summary
    horizontal_summary = "=== HORIZONTAL ANALYSIS (Cross-Sector Portfolio) ===\n"
    if isinstance(horizontal_result, dict):
        if 'portfolio' in horizontal_result:
            portfolio = horizontal_result['portfolio']
            if isinstance(portfolio, pd.DataFrame) and len(portfolio) > 0:
                horizontal_summary += "Selected Portfolio:\n"
                for _, row in portfolio.iterrows():
                    ticker = row.get('ticker', 'N/A')
                    weight = row.get('weight', 0) * 100
                    sector = row.get('sector', 'N/A')
                    horizontal_summary += f"  - {ticker}: {weight:.1f}% ({sector})\n"
        
        if 'risk_metrics' in horizontal_result:
            metrics = horizontal_result['risk_metrics']
            horizontal_summary += "\nRisk Metrics:\n"
            for key, val in metrics.items():
                if isinstance(val, float):
                    horizontal_summary += f"  - {key}: {val:.4f}\n"
    
    # Prepare backtest summary
    backtest_summary = "=== BACKTEST PERFORMANCE ===\n"
    for key, val in backtest_metrics.items():
        if isinstance(val, (int, float)):
            if 'return' in key.lower() or 'drawdown' in key.lower() or 'volatility' in key.lower():
                backtest_summary += f"  - {key}: {val*100:.2f}%\n"
            elif 'ratio' in key.lower():
                backtest_summary += f"  - {key}: {val:.2f}\n"
            else:
                backtest_summary += f"  - {key}: {val}\n"
    
    # Prepare all candidates summary
    candidates_summary = "=== ALL CANDIDATES ===\n"
    if isinstance(all_candidates, pd.DataFrame) and len(all_candidates) > 0:
        cols = ['ticker', 'sector', 'score', 'domain_score', 'value_score', 'quality_score', 'volatility_annual']
        available_cols = [c for c in cols if c in all_candidates.columns]
        
        # Sort by score/domain_score
        sort_col = 'domain_score' if 'domain_score' in all_candidates.columns else 'score'
        sorted_df = all_candidates.sort_values(sort_col, ascending=False).head(30)
        
        for _, row in sorted_df.iterrows():
            parts = []
            for col in available_cols:
                val = row.get(col)
                if val is not None:
                    if col == 'volatility_annual':
                        parts.append(f"vol={val*100:.1f}%")
                    elif isinstance(val, float):
                        parts.append(f"{col}={val:.1f}")
                    else:
                        parts.append(f"{col}={val}")
            candidates_summary += f"  {', '.join(parts)}\n"
    
    # Build the full prompt
    prompt = f"""{RECOMMENDATION_PROMPT}

{vertical_summary}

{horizontal_summary}

{backtest_summary}

{candidates_summary}

Please provide your portfolio recommendations in the following JSON structure:

```json
{{
  "conservative": {{
    "name": "Conservative Portfolio",
    "risk_level": "Low",
    "time_horizon": "1-3 years",
    "target_volatility": "12-15%",
    "holdings": [
      {{"ticker": "XXX", "weight": 15, "rationale": "..."}},
      ...
    ],
    "expected_return": {{
      "low": 5,
      "mid": 8,
      "high": 12
    }},
    "risk_assessment": {{
      "volatility": "12-15%",
      "max_drawdown": "10-15%",
      "key_risks": ["..."]
    }},
    "rebalance_frequency": "Quarterly"
  }},
  "balanced": {{
    ...
  }},
  "aggressive": {{
    ...
  }},
  "overall_assessment": "..."
}}
```

Ensure weights in each portfolio sum to 100%.
"""

    try:
        response = client.generate_content(prompt)
        response_text = response.text
        
        # Try to parse JSON from response
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            recommendations = json.loads(json_str)
            return {
                'recommendations': recommendations,
                'raw_response': response_text,
                'generated_at': datetime.now().isoformat(),
            }
        else:
            # Return raw response if JSON parsing fails
            return {
                'recommendations': None,
                'raw_response': response_text,
                'generated_at': datetime.now().isoformat(),
                'parse_error': 'Could not extract JSON from response'
            }
            
    except Exception as e:
        return {
            'recommendations': None,
            'error': str(e),
            'generated_at': datetime.now().isoformat(),
        }


def save_recommendations_to_file(
    recommendations: Dict[str, Any],
    run_id: str,
    output_dir: str = "output",
) -> Path:
    """Save portfolio recommendations to files (JSON and Markdown)."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save JSON
    json_file = output_path / f"recommendations_{run_id[:16]}_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(recommendations, f, indent=2, default=str)
    
    # Generate Markdown report
    md_content = f"""# Portfolio Recommendations

**Run ID**: {run_id}
**Generated**: {recommendations.get('generated_at', 'N/A')}

---

"""
    
    recs = recommendations.get('recommendations', {})
    if recs:
        for profile in ['conservative', 'balanced', 'aggressive']:
            if profile in recs:
                rec = recs[profile]
                md_content += f"""
## {rec.get('name', profile.title())}

**Risk Level**: {rec.get('risk_level', 'N/A')}
**Time Horizon**: {rec.get('time_horizon', 'N/A')}
**Target Volatility**: {rec.get('target_volatility', 'N/A')}
**Rebalance**: {rec.get('rebalance_frequency', 'N/A')}

### Holdings

| Ticker | Weight | Rationale |
|--------|--------|-----------|
"""
                for holding in rec.get('holdings', []):
                    md_content += f"| {holding.get('ticker', 'N/A')} | {holding.get('weight', 0)}% | {holding.get('rationale', '')} |\n"
                
                expected = rec.get('expected_return', {})
                md_content += f"""
### Expected Return
- **Low Scenario**: {expected.get('low', 'N/A')}%
- **Mid Scenario**: {expected.get('mid', 'N/A')}%
- **High Scenario**: {expected.get('high', 'N/A')}%

### Risk Assessment
"""
                risk = rec.get('risk_assessment', {})
                md_content += f"- **Volatility**: {risk.get('volatility', 'N/A')}\n"
                md_content += f"- **Max Drawdown**: {risk.get('max_drawdown', 'N/A')}\n"
                md_content += f"- **Key Risks**: {', '.join(risk.get('key_risks', []))}\n"
                
                md_content += "\n---\n"
        
        if 'overall_assessment' in recs:
            md_content += f"\n## Overall Assessment\n\n{recs['overall_assessment']}\n"
    else:
        md_content += "**Note**: Could not generate structured recommendations.\n\n"
        md_content += f"Raw Response:\n\n{recommendations.get('raw_response', 'No response')}\n"
    
    md_content += """
---

*⚠️ DISCLAIMER: These recommendations are for educational purposes only and do not constitute financial advice. 
Past performance does not guarantee future results. Always consult a qualified financial advisor before investing.*
"""
    
    md_file = output_path / f"recommendations_{run_id[:16]}_{timestamp}.md"
    with open(md_file, 'w') as f:
        f.write(md_content)
    
    return md_file


def save_commentary_to_file(
    commentary: str,
    run_id: str,
    output_dir: str = "output",
    commentary_type: str = "portfolio"
) -> Path:
    """Save commentary to a markdown file."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"commentary_{commentary_type}_{run_id[:16]}_{timestamp}.md"
    filepath = output_path / filename
    
    content = f"""# Portfolio Commentary

**Run ID**: {run_id}
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Type**: {commentary_type}

---

{commentary}

---

*This commentary was generated by Gemini for explanation purposes only. 
All portfolio decisions were made through quantitative analysis.*
"""
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    return filepath


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Generate commentary for the latest run."""
    import argparse
    import sys
    
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    parser = argparse.ArgumentParser(description="Generate Gemini commentary for portfolio analysis")
    parser.add_argument("--run-id", type=str, help="Specific run ID (default: latest)")
    parser.add_argument("--output", type=str, default="output", help="Output directory")
    parser.add_argument("--type", choices=['portfolio', 'risk', 'comparison'], default='portfolio')
    
    args = parser.parse_args()
    
    # Check if Gemini is available
    client = get_gemini_client()
    if client is None:
        print("❌ Gemini API not available. Set GEMINI_API_KEY environment variable.")
        return 1
    
    print("🤖 Gemini Commentary Generator")
    print("=" * 50)
    print("NOTE: Gemini provides COMMENTARY ONLY")
    print("      All portfolio decisions are numeric.")
    print("=" * 50)
    
    # Load data
    from src.analytics.models import get_db, Run, StockScore
    
    db = get_db("data/analysis.db")
    session = db.get_session()
    
    try:
        # Get run
        if args.run_id:
            run = session.query(Run).filter_by(run_id=args.run_id).first()
        else:
            run = session.query(Run).order_by(Run.created_at.desc()).first()
        
        if not run:
            print("❌ No runs found")
            return 1
        
        print(f"\n📊 Analyzing run: {run.run_id}")
        
        # Get scores
        scores = session.query(StockScore).filter_by(run_id=run.run_id).all()
        scores_df = pd.DataFrame([s.to_dict() for s in scores])
        
        # Build metrics
        metrics = {
            'sharpe_ratio': run.sharpe_ratio or 0,
            'max_drawdown': run.max_drawdown or 0,
            'total_return': run.total_return or 0,
            'volatility': run.volatility or 0,
        }
        
        # Load additional metrics if available
        metrics_path = Path(args.output) / f"portfolio_metrics_{run.run_id[:16]}.json"
        if metrics_path.exists():
            with open(metrics_path) as f:
                saved_metrics = json.load(f)
                if 'metrics' in saved_metrics:
                    metrics.update(saved_metrics['metrics'])
        
        # Generate commentary
        print("\n✍️ Generating commentary...")
        
        if args.type == 'portfolio':
            commentary = generate_portfolio_commentary(scores_df, metrics)
        elif args.type == 'risk':
            sector_weights = None
            if 'sector' in scores_df.columns:
                sector_weights = scores_df.groupby('sector').size() / len(scores_df)
                sector_weights = sector_weights.to_dict()
            commentary = generate_risk_commentary(metrics, len(scores_df), sector_weights)
        else:
            print("Comparison requires two runs - use dashboard instead")
            return 1
        
        if commentary:
            print("\n" + "=" * 50)
            print(commentary)
            print("=" * 50)
            
            # Save to file
            filepath = save_commentary_to_file(commentary, run.run_id, args.output, args.type)
            print(f"\n✅ Saved to: {filepath}")
        else:
            print("❌ Failed to generate commentary")
            return 1
        
    finally:
        session.close()
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
