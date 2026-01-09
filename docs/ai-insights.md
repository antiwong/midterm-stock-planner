# AI-Powered Analysis Insights

This document describes the Gemini-powered AI insights feature for generating detailed explanations and recommendations.

## Overview

The AI Insights module uses Google's Gemini LLM to:

1. **Explain** analysis results in plain language
2. **Interpret** model scores and rankings
3. **Recommend** specific actions based on the data
4. **Warn** about risks and concentrations
5. **Summarize** complex portfolio analytics
6. **Generate** personalized portfolio recommendations (NEW)
7. **Analyze** investor profiles against portfolio characteristics (NEW)

**Important:** AI insights are supplementary to numeric analysis. The primary source of truth is always the deterministic data pipeline. AI does NOT change tickers, weights, or make trading decisions.

## Module Location

```
src/analytics/ai_insights.py
```

## Setup

### API Key Configuration

1. Get a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

2. Add to `.env` file in project root:
```bash
GEMINI_API_KEY=your-api-key-here
```

3. Load in your code:
```python
from src.config.api_keys import load_api_keys
load_api_keys()
```

### Dependencies

```bash
pip install google-generativeai python-dotenv
```

## AIInsightsGenerator Class

```python
from src.analytics.ai_insights import AIInsightsGenerator

generator = AIInsightsGenerator(
    api_key=None,  # Uses GEMINI_API_KEY env var if not provided
    model_name="gemini-2.0-flash",  # Default model
)

# Check availability
if generator.is_available:
    print("Gemini AI ready")
```

## Portfolio Insights

Generate comprehensive insights for an analysis run:

```python
insights = generator.generate_portfolio_insights(
    top_stocks=[
        {"ticker": "NVDA", "score": 0.85, "tech_score": 0.9, ...},
        {"ticker": "AAPL", "score": 0.75, ...},
    ],
    bottom_stocks=[
        {"ticker": "XOM", "score": 0.35, ...},
    ],
    sector_breakdown={
        "Technology": {"score": 0.75, "count": 10},
        "Healthcare": {"score": 0.60, "count": 5},
    },
    model_metrics={
        "spearman_corr": 0.18,
        "hit_rate": 0.62,
        "sharpe_ratio": 0.55,
    },
    run_name="Q1 2025 Analysis",
)
```

### Generated Sections

| Section | Content |
|---------|---------|
| `executive_summary` | 3-4 paragraph overview with key findings |
| `top_picks_analysis` | Detailed analysis of top 5 stocks |
| `sector_analysis` | Sector rotation and allocation guidance |
| `risk_assessment` | Risk factors and hedging suggestions |
| `recommendations` | Actionable buy/sell/watch recommendations |

## Individual Stock Insights

Generate AI analysis for a single stock:

```python
insight = generator.generate_stock_insight(
    ticker="NVDA",
    score_data={
        "score": 0.85,
        "rank": 1,
        "tech_score": 0.9,
        "fund_score": 0.8,
        "sent_score": 0.7,
        "rsi": 55,
        "return_21d": 0.05,
        "return_63d": 0.12,
        "volatility": 0.45,
        "sector": "Technology",
    }
)
print(insight)
```

## Risk-Aware Insights

Generate insights for risk-parity allocation:

```python
risk_insights = generator.generate_risk_aware_insights(
    positions=[
        {"ticker": "AAPL", "risk_weight": 0.08, "volatility": 0.25, "beta": 1.1, ...},
    ],
    risk_profile={
        "total_beta": 1.05,
        "weighted_avg_vol": 0.28,
        "portfolio_vol_estimate": 0.15,
        "sector_exposure": {"Technology": 0.30, ...},
        "beta_exposure": {"Low (<0.8)": 0.2, "Medium (0.8-1.2)": 0.6, "High (>1.2)": 0.2},
        "concentration_hhi": 850,
        "effective_n": 15.5,
        "risk_tilt": "Balanced",
    },
    comparison={  # Optional: Equal weight vs risk parity comparison
        "ew_beta": 1.15,
        "rp_beta": 1.05,
        "ew_vol": 0.20,
        "rp_vol": 0.15,
        "sharpe_improvement": 0.10,
    },
)
```

### Risk Insight Sections

| Section | Content |
|---------|---------|
| `allocation_rationale` | Why risk parity was applied |
| `beta_analysis` | Beta exposure and market sensitivity |
| `sizing_recommendations` | Position adjustments and rebalancing |

## Integration with Reports

AI insights are automatically included in generated reports:

```python
from src.analytics import ReportGenerator

generator = ReportGenerator(enable_ai_insights=True)
reports = generator.generate_report(
    run_id="20251231_091426_abc123",
    format="all",
    include_ai_insights=True,
)
```

### HTML Report

AI sections are styled with special formatting:
- Blue gradient background for AI sections
- "Powered by Gemini" badge
- Clear visual distinction from numeric data

### Markdown Report

AI sections use emoji headers:
- 🤖 AI Executive Summary
- 🎯 AI Top Picks Analysis
- 📊 AI Sector Analysis
- ⚠️ AI Risk Assessment
- 💡 AI Investment Recommendations

## Dashboard Integration

The Streamlit dashboard includes an AI Insights page:

1. Select an analysis run
2. Click "Generate AI Insights"
3. View insights in tabbed interface
4. Generate individual stock analysis

```python
# Access from sidebar
page = "🤖 AI Insights"
```

## Portfolio Commentary

Generate comprehensive commentary for analysis runs:

```python
from src.analysis.gemini_commentary import (
    generate_portfolio_commentary,
    save_commentary_to_file,
)

commentary = generate_portfolio_commentary(
    portfolio_df=portfolio_holdings,
    metrics={
        'total_return': 0.15,
        'sharpe_ratio': 1.2,
        'max_drawdown': -0.10,
    },
    run_id="20251231_115520",
    config=config,
)

# Save to file
save_commentary_to_file(commentary, run_id, output_dir)
```

Output: `commentary_{run_id}.md`

### Commentary Sections

- **Portfolio Summary**: Overview of holdings and characteristics
- **Concentration Analysis**: Sector/position concentration risks
- **Style Analysis**: Growth/value tilt identification
- **Risk Commentary**: Risk factors and mitigation suggestions

## Portfolio Recommendations

Generate personalized recommendations based on investor profile:

```python
from src.analysis.gemini_commentary import (
    generate_portfolio_recommendations,
    save_recommendations_to_file,
)

recommendations = generate_portfolio_recommendations(
    all_stocks_df=scores_df,
    portfolio_df=optimized_holdings,
    metrics=portfolio_metrics,
    config=config,
)

# Save to file
save_recommendations_to_file(recommendations, run_id, output_dir, format="md")
```

Output: `recommendations_{run_id}.md` and `recommendations_{run_id}.json`

### Recommendation Profiles

The AI generates three portfolio profiles:

| Profile | Risk Level | Expected Return | Time Horizon |
|---------|------------|-----------------|--------------|
| **Conservative** | Low | 6-8% | 12+ months |
| **Balanced** | Medium | 10-15% | 6-12 months |
| **Aggressive** | High | 15-25% | 3-6 months |

Each profile includes:
- Suggested holdings (tickers)
- Position weights
- Risk assessment
- Expected return range
- Investment rationale

## Personalized Portfolio Analysis

Generate AI analysis for Portfolio Builder results:

```python
from src.analysis.portfolio_optimizer import generate_ai_analysis

result = optimizer.optimize(stocks_df, price_df)
ai_analysis = generate_ai_analysis(result)
```

The AI analyzes:
1. **Profile Alignment**: How well portfolio matches investor preferences
2. **Risk Analysis**: Key risks relative to stated tolerance
3. **Sector Commentary**: Sector allocation rationale
4. **Top Holdings**: Analysis of largest positions
5. **Recommendations**: Adjustments or considerations
6. **Time Horizon**: Suitability for stated holding period

## Fallback Behavior

When Gemini is unavailable, the system provides:
- Basic rule-based insights
- Score summaries
- Simple buy/hold/avoid ratings

```python
# Check availability
if not generator.is_available:
    print("Using fallback insights (AI unavailable)")
```

## Prompt Engineering

The module uses carefully crafted prompts for each section:

### Executive Summary Prompt
```
Based on the stock analysis results below, provide a concise executive summary 
(3-4 paragraphs) covering:
1. Overall market positioning and key findings
2. Top opportunities identified
3. Key risks and considerations
4. Investment outlook for the next 3 months

Be specific about stock symbols and numbers. Use professional investment language.
```

### Recommendations Prompt
```
Based on all the analysis results below, provide specific actionable recommendations:
1. BUY recommendations (3-5 stocks with target allocation %)
2. AVOID/SELL recommendations with reasoning
3. WATCH LIST (stocks to monitor for entry)
4. Rebalancing suggestions
5. Position sizing guidance
6. Time horizon and review schedule

Be specific with entry points, stop-loss levels where applicable.
```

## Best Practices

### DO

✅ Use AI to **explain** existing numeric results
✅ Use AI to **summarize** complex analytics
✅ Use AI to **highlight** risks visible in data
✅ Use AI to **suggest** additional diagnostics
✅ Always include disclaimer in reports

### DON'T

❌ Let AI **invent** new signals or scores
❌ Let AI **change** tickers or weights
❌ Let AI make **trading decisions**
❌ Use AI output without reviewing numeric data first

## Disclaimer

Always include this disclaimer with AI-generated content:

> *The AI-generated insights are for informational purposes only and do not 
> constitute financial advice. Past performance is not indicative of future 
> results. Always conduct your own research and consult with qualified 
> financial advisors before making investment decisions.*

## Configuration

Generation parameters can be adjusted:

```python
response = self._model.generate_content(
    prompt,
    generation_config={
        "temperature": 0.7,      # Creativity (0-1)
        "max_output_tokens": 1500,  # Response length
    }
)
```

## Error Handling

The module gracefully handles errors:

```python
try:
    insight = generator.generate_stock_insight(ticker, data)
except Exception as e:
    insight = generator._generate_stock_fallback(ticker, data)
```

## Cost Considerations

- Gemini API has usage limits and costs
- Each insight generation makes 5 API calls (one per section)
- Consider caching insights for repeated views
- Use `enable_ai_insights=False` for bulk operations

## Troubleshooting

### "AI not available"

1. Check GEMINI_API_KEY is set
2. Verify API key is valid
3. Check network connectivity
4. Ensure `google-generativeai` is installed

### "Insufficient quota"

- Check Google AI Studio for usage limits
- Wait for quota reset or upgrade plan

### Slow generation

- Each section takes 2-5 seconds
- Consider generating asynchronously for better UX
