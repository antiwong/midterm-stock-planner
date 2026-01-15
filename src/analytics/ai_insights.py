"""
AI-Powered Analysis Insights
============================
Use Gemini LLM to generate detailed explanations and recommendations.
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import warnings
import hashlib

# Load API keys
from src.config.api_keys import load_api_keys
load_api_keys()

# Import analysis service for database operations
try:
    from .analysis_service import AnalysisService
    ANALYSIS_SERVICE_AVAILABLE = True
except ImportError:
    ANALYSIS_SERVICE_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    warnings.warn("google-generativeai not installed. AI insights disabled.")

try:
    from src.risk.risk_parity import PortfolioRiskProfile
    RISK_PARITY_AVAILABLE = True
except ImportError:
    RISK_PARITY_AVAILABLE = False


class AIInsightsGenerator:
    """
    Generates AI-powered insights and recommendations using Gemini.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = None,
        save_to_db: bool = True,
        db_path: str = "data/analysis.db"
    ):
        """
        Initialize the AI insights generator.
        
        Args:
            api_key: Gemini API key (or uses GEMINI_API_KEY env var)
            model_name: Gemini model to use (auto-detects if None)
            save_to_db: Whether to save insights to database
            db_path: Path to analysis database
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name
        self._model = None
        self.save_to_db = save_to_db and ANALYSIS_SERVICE_AVAILABLE
        if self.save_to_db:
            self.analysis_service = AnalysisService(db_path)
        
        if GEMINI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                
                # Try different model names in order of preference
                model_names = [model_name] if model_name else []
                model_names.extend([
                    'gemini-2.0-flash-exp',
                    'gemini-1.5-flash-latest',
                    'gemini-1.5-pro-latest',
                    'gemini-pro',
                ])
                
                for name in model_names:
                    if name is None:
                        continue
                    try:
                        self._model = genai.GenerativeModel(name)
                        self.model_name = name
                        break
                    except Exception:
                        continue
                        
            except Exception as e:
                warnings.warn(f"Failed to initialize Gemini: {e}")
    
    @property
    def is_available(self) -> bool:
        """Check if AI insights are available."""
        return self._model is not None
    
    def generate_portfolio_insights(
        self,
        top_stocks: List[Dict[str, Any]],
        bottom_stocks: List[Dict[str, Any]],
        sector_breakdown: Dict[str, Dict[str, float]],
        model_metrics: Dict[str, float],
        run_name: str = "Analysis",
        run_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Generate comprehensive AI insights for the portfolio analysis.
        
        Args:
            top_stocks: List of top-ranked stocks with scores
            bottom_stocks: List of bottom-ranked stocks
            sector_breakdown: Sector performance breakdown
            model_metrics: Model performance metrics
            run_name: Name of the analysis run
            run_id: Run ID for database storage (optional)
            
        Returns:
            Dictionary with different insight sections
        """
        if not self.is_available:
            insights = self._generate_fallback_insights(top_stocks, sector_breakdown)
            if self.save_to_db and run_id:
                self._save_insights_to_db(run_id, insights, context={})
            return insights
        
        # Build the analysis context
        context = self._build_context(
            top_stocks, bottom_stocks, sector_breakdown, model_metrics
        )
        
        # Create context dict for database storage
        context_dict = {
            'top_stocks': top_stocks[:10],
            'bottom_stocks': bottom_stocks[:5],
            'sector_breakdown': sector_breakdown,
            'model_metrics': {k: v for k, v in model_metrics.items() 
                            if k not in ['data_quality', 'data_errors', 'data_warnings']}
        }
        
        insights = {}
        
        # Generate executive summary
        insights['executive_summary'] = self._generate_section(
            "executive_summary", context
        )
        if self.save_to_db and run_id:
            self.analysis_service.save_ai_insight(
                run_id=run_id,
                insight_type='executive_summary',
                content=insights['executive_summary'],
                context=context_dict,
                model=self.model_name or 'gemini',
                prompt_hash=self._hash_context(context_dict)
            )
        
        # Generate top picks analysis
        insights['top_picks_analysis'] = self._generate_section(
            "top_picks", context
        )
        if self.save_to_db and run_id:
            self.analysis_service.save_ai_insight(
                run_id=run_id,
                insight_type='top_picks_analysis',
                content=insights['top_picks_analysis'],
                context=context_dict,
                model=self.model_name or 'gemini',
                prompt_hash=self._hash_context(context_dict)
            )
        
        # Generate sector analysis
        insights['sector_analysis'] = self._generate_section(
            "sector_analysis", context
        )
        if self.save_to_db and run_id:
            self.analysis_service.save_ai_insight(
                run_id=run_id,
                insight_type='sector_analysis',
                content=insights['sector_analysis'],
                context=context_dict,
                model=self.model_name or 'gemini',
                prompt_hash=self._hash_context(context_dict)
            )
        
        # Generate risk assessment
        insights['risk_assessment'] = self._generate_section(
            "risk_assessment", context
        )
        if self.save_to_db and run_id:
            self.analysis_service.save_ai_insight(
                run_id=run_id,
                insight_type='risk_assessment',
                content=insights['risk_assessment'],
                context=context_dict,
                model=self.model_name or 'gemini',
                prompt_hash=self._hash_context(context_dict)
            )
        
        # Generate actionable recommendations
        insights['recommendations'] = self._generate_section(
            "recommendations", context
        )
        if self.save_to_db and run_id:
            # Try to extract structured recommendations
            recommendations_json = self._extract_recommendations(insights['recommendations'])
            self.analysis_service.save_ai_insight(
                run_id=run_id,
                insight_type='recommendations',
                content=insights['recommendations'],
                content_json=recommendations_json,
                context=context_dict,
                model=self.model_name or 'gemini',
                prompt_hash=self._hash_context(context_dict)
            )
        
        return insights
    
    def _hash_context(self, context: Dict) -> str:
        """Generate hash of context for deduplication."""
        context_str = json.dumps(context, sort_keys=True, default=str)
        return hashlib.sha256(context_str.encode()).hexdigest()
    
    def _extract_recommendations(self, recommendations_text: str) -> Dict:
        """Extract structured recommendations from text."""
        # Simple extraction - can be enhanced
        return {
            'text': recommendations_text,
            'extracted': False  # Placeholder for future NLP extraction
        }
    
    def _save_insights_to_db(self, run_id: str, insights: Dict, context: Dict):
        """Save fallback insights to database."""
        for insight_type, content in insights.items():
            try:
                self.analysis_service.save_ai_insight(
                    run_id=run_id,
                    insight_type=insight_type,
                    content=content,
                    context=context,
                    model='fallback',
                    status='completed'
                )
            except Exception as e:
                print(f"Error saving {insight_type} to DB: {e}")
    
    def _build_context(
        self,
        top_stocks: List[Dict],
        bottom_stocks: List[Dict],
        sector_breakdown: Dict,
        model_metrics: Dict,
    ) -> str:
        """Build context string for the LLM."""
        
        # Format top stocks
        top_stocks_str = "\n".join([
            f"  {i+1}. {s['ticker']} - Score: {s['score']:.4f}, "
            f"Tech: {s.get('tech_score', 0):.3f}, Fund: {s.get('fund_score', 0):.3f}, "
            f"Sent: {s.get('sent_score', 0):.3f}, RSI: {s.get('rsi', 50):.0f}, "
            f"21d Return: {s.get('return_21d', 0)*100:+.1f}%"
            for i, s in enumerate(top_stocks[:10])
        ])
        
        # Format bottom stocks
        bottom_stocks_str = "\n".join([
            f"  {s['ticker']} - Score: {s['score']:.4f}, "
            f"21d Return: {s.get('return_21d', 0)*100:+.1f}%"
            for s in bottom_stocks[:5]
        ])
        
        # Format sectors
        sector_str = "\n".join([
            f"  {sector}: Avg Score {data.get('score', 0):.3f} ({data.get('count', 0)} stocks)"
            for sector, data in sorted(
                sector_breakdown.items(), 
                key=lambda x: x[1].get('score', 0), 
                reverse=True
            )
        ])
        
        # Format metrics (excluding data quality fields)
        metrics_str = "\n".join([
            f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}"
            for k, v in model_metrics.items()
            if k not in ['data_quality', 'data_errors', 'data_warnings']
        ])
        
        # Initialize data quality note
        data_quality_note = ""
        
        # Check for identical sector scores (data quality issue)
        if sector_breakdown:
            sector_scores = [data.get('score', 0) for data in sector_breakdown.values()]
            if len(set(sector_scores)) == 1 and sector_scores[0] == 0.0:
                data_quality_note += "\n\n🚨 CRITICAL: All sectors have identical scores (0.000). This indicates a severe data normalization or calculation issue. DO NOT provide sector allocation recommendations."
        
        # Add data quality warnings if present
        if model_metrics.get('data_quality') == 'ERRORS_DETECTED':
            errors = model_metrics.get('data_errors', [])
            data_quality_note = f"\n\n🚨 CRITICAL DATA QUALITY ERRORS DETECTED:\n" + "\n".join([f"  - {e}" for e in errors[:5]])
            data_quality_note += "\n\n⚠️ DO NOT PROVIDE INVESTMENT RECOMMENDATIONS. The data is unreliable and any analysis based on this data would be misleading."
            data_quality_note += "\n\nREQUIRED ACTIONS:\n  1. Fix the data quality issues identified above\n  2. Re-run the analysis with corrected data\n  3. Only then provide investment recommendations"
            data_quality_note += "\n\nIf you must provide any guidance, focus ONLY on:\n  - Identifying what data issues need to be fixed\n  - Explaining why recommendations cannot be made\n  - Suggesting diagnostic steps to resolve the issues"
        elif model_metrics.get('data_quality') == 'WARNINGS':
            warnings = model_metrics.get('data_warnings', [])
            data_quality_note = f"\n\n⚠️ DATA QUALITY WARNINGS:\n" + "\n".join([f"  - {w}" for w in warnings[:5]])
            data_quality_note += "\n\nPlease interpret the analysis below with EXTREME CAUTION. If sector scores are identical or data shows poor differentiation, DO NOT provide specific allocation recommendations."
        
        context = f"""
STOCK ANALYSIS RESULTS
======================
Analysis Date: {datetime.now().strftime('%Y-%m-%d')}
{data_quality_note}

MODEL PERFORMANCE:
{metrics_str}

TOP 10 RANKED STOCKS:
{top_stocks_str}

BOTTOM 5 STOCKS:
{bottom_stocks_str}

SECTOR BREAKDOWN:
{sector_str}

SCORING METHODOLOGY:
- Technical Score (50%): ML model predictions based on price momentum, volatility, RSI, MACD
- Fundamental Score (30%): Valuation, profitability, and growth metrics
- Sentiment Score (20%): News sentiment analysis

Note: This is a 3-month investment horizon analysis with monthly rebalancing.
"""
        return context
    
    def _generate_section(self, section_type: str, context: str) -> str:
        """Generate a specific insight section."""
        
        prompts = {
            "executive_summary": """
Based on the stock analysis results below, provide a concise executive summary (3-4 paragraphs) covering:
1. Overall market positioning and key findings
2. Top opportunities identified
3. Key risks and considerations
4. Investment outlook for the next 3 months

Be specific about stock symbols and numbers. Use professional investment language.
""",
            "top_picks": """
Based on the analysis results below, provide detailed analysis of the TOP 5 stocks:
For each stock:
1. Why it ranks highly (technical, fundamental, sentiment factors)
2. Key strengths and potential catalysts
3. Risk factors to watch
4. Suggested position sizing (conservative/moderate/aggressive)

Format each stock analysis clearly with the ticker as a header.
""",
            "sector_analysis": """
Based on the sector breakdown in the analysis results below:
1. Which sectors show the strongest positioning and why
2. Which sectors appear overvalued or risky
3. Sector rotation recommendations
4. Cross-sector correlation observations

CRITICAL: If you see data quality warnings/errors in the context, or if all sectors have identical scores (especially 0.000), DO NOT provide sector allocation guidance. Instead, clearly state that the data is unreliable and recommend fixing the data quality issues before making any investment decisions.

Provide actionable sector allocation guidance ONLY if the data appears valid and sectors show meaningful differentiation.
""",
            "risk_assessment": """
Based on the analysis results below, provide a comprehensive risk assessment:
1. Portfolio concentration risks
2. Volatility and drawdown expectations
3. Correlation risks among top holdings
4. Market regime considerations
5. Specific stock-level risks for top picks
6. Hedging suggestions

Rate overall portfolio risk as Low/Medium/High with explanation.
""",
            "recommendations": """
Based on all the analysis results below, provide specific actionable recommendations:
1. BUY recommendations (3-5 stocks with target allocation %)
2. AVOID/SELL recommendations with reasoning
3. WATCH LIST (stocks to monitor for entry)
4. Rebalancing suggestions
5. Position sizing guidance
6. Time horizon and review schedule

Be specific with entry points, stop-loss levels where applicable.

CRITICAL DATA QUALITY CHECK:
- If you see data quality warnings/errors in the context above, DO NOT provide specific investment recommendations.
- If all sectors have identical scores (especially 0.000), this indicates a data normalization issue - DO NOT provide sector allocation guidance.
- Instead, clearly state: "Data quality issues detected. Recommendations cannot be provided until data issues are resolved. Please investigate and fix the data quality problems before making investment decisions."
- Only provide recommendations if the data appears valid, sectors show meaningful differentiation, and stock scores are properly distributed.
"""
        }
        
        prompt = prompts.get(section_type, prompts["executive_summary"])
        full_prompt = f"{prompt}\n\n{context}"
        
        try:
            response = self._model.generate_content(
                full_prompt,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 1500,
                }
            )
            return response.text.strip()
        except Exception as e:
            return f"[AI insight generation failed: {e}]"
    
    def _generate_fallback_insights(
        self,
        top_stocks: List[Dict],
        sector_breakdown: Dict,
    ) -> Dict[str, str]:
        """Generate basic insights when AI is not available."""
        
        # Executive summary
        top_tickers = [s['ticker'] for s in top_stocks[:5]]
        avg_score = sum(s['score'] for s in top_stocks[:10]) / min(10, len(top_stocks))
        
        exec_summary = f"""
## Executive Summary

This analysis identified {len(top_stocks)} stocks for potential investment opportunities.

**Top Recommendations:** {', '.join(top_tickers)}

The average score for the top 10 stocks is {avg_score:.4f}, indicating 
{'strong' if avg_score > 0.6 else 'moderate' if avg_score > 0.4 else 'weak'} 
overall signal strength.

**Sector Leaders:** {', '.join(list(sector_breakdown.keys())[:3])}

*Note: AI-powered detailed analysis is not available. Enable Gemini API for enhanced insights.*
"""
        
        # Top picks
        top_picks = "## Top Stock Analysis\n\n"
        for i, stock in enumerate(top_stocks[:5], 1):
            top_picks += f"""
### {i}. {stock['ticker']}
- **Overall Score:** {stock['score']:.4f}
- **Technical Score:** {stock.get('tech_score', 0):.3f}
- **Fundamental Score:** {stock.get('fund_score', 0):.3f}
- **Sentiment Score:** {stock.get('sent_score', 0):.3f}
- **RSI:** {stock.get('rsi', 50):.0f}
- **21-Day Return:** {stock.get('return_21d', 0)*100:+.1f}%

"""
        
        return {
            'executive_summary': exec_summary,
            'top_picks_analysis': top_picks,
            'sector_analysis': "Sector analysis requires AI insights to be enabled.",
            'risk_assessment': "Risk assessment requires AI insights to be enabled.",
            'recommendations': "Detailed recommendations require AI insights to be enabled.",
        }
    
    def generate_stock_insight(
        self,
        ticker: str,
        score_data: Dict[str, Any],
        price_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate detailed insight for a single stock.
        
        Args:
            ticker: Stock ticker symbol
            score_data: Score breakdown and features
            price_data: Optional price/volume data
            
        Returns:
            Detailed stock analysis text
        """
        if not self.is_available:
            return self._generate_stock_fallback(ticker, score_data)
        
        # Safely extract values, handling None
        score = score_data.get('score') or 0
        rank = score_data.get('rank') or 'N/A'
        tech_score = score_data.get('tech_score') or 0
        fund_score = score_data.get('fund_score') or 0
        sent_score = score_data.get('sent_score') or 0
        rsi = score_data.get('rsi') or 50
        return_21d = (score_data.get('return_21d') or 0) * 100
        return_63d = (score_data.get('return_63d') or 0) * 100
        volatility = (score_data.get('volatility') or 0) * 100
        sector = score_data.get('sector') or 'Unknown'
        
        context = f"""
STOCK: {ticker}
Score: {score:.4f} (Rank #{rank})

Score Breakdown:
- Technical: {tech_score:.3f}
- Fundamental: {fund_score:.3f}
- Sentiment: {sent_score:.3f}

Key Metrics:
- RSI (14): {rsi:.1f}
- 21-Day Return: {return_21d:+.1f}%
- 63-Day Return: {return_63d:+.1f}%
- Volatility (21d): {volatility:.1f}%
- Sector: {sector}
"""
        
        prompt = f"""
Provide a concise investment analysis for this stock (2-3 paragraphs):
1. Overall assessment and key drivers of the score
2. Technical outlook based on RSI and momentum
3. Risk factors and recommendation (Buy/Hold/Avoid)

{context}
"""
        
        try:
            response = self._model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 500,
                }
            )
            return response.text.strip()
        except Exception as e:
            return self._generate_stock_fallback(ticker, score_data)
    
    def generate_executive_summary(
        self,
        scores: List[Dict[str, Any]],
        validation_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate an executive summary from stock scores.
        
        Convenience method that extracts data from scores list and
        calls generate_portfolio_insights.
        
        Args:
            scores: List of stock score dictionaries
            
        Returns:
            Executive summary text
        """
        if not scores:
            return "No data available for executive summary."
        
        # Sort by score and get top/bottom
        sorted_scores = sorted(scores, key=lambda x: x.get('score', 0), reverse=True)
        top_stocks = sorted_scores[:10]
        bottom_stocks = sorted_scores[-5:] if len(sorted_scores) > 5 else []
        
        # Build sector breakdown
        sector_breakdown = {}
        for s in scores:
            sector = s.get('sector', 'Other')
            if sector not in sector_breakdown:
                sector_breakdown[sector] = {'count': 0, 'avg_score': 0, 'scores': []}
            sector_breakdown[sector]['count'] += 1
            sector_breakdown[sector]['scores'].append(s.get('score', 0))
        
        for sector in sector_breakdown:
            scores_list = sector_breakdown[sector]['scores']
            sector_breakdown[sector]['avg_score'] = sum(scores_list) / len(scores_list) if scores_list else 0
            del sector_breakdown[sector]['scores']
        
        # Add validation warnings to context if present
        model_metrics = {'total_stocks': len(scores)}
        if validation_context:
            if validation_context.get('has_errors'):
                model_metrics['data_quality'] = 'ERRORS_DETECTED'
                model_metrics['data_errors'] = validation_context.get('errors', [])
            if validation_context.get('warnings'):
                model_metrics['data_quality'] = 'WARNINGS'
                model_metrics['data_warnings'] = validation_context.get('warnings', [])
        
        # Generate insights
        insights = self.generate_portfolio_insights(
            top_stocks=top_stocks,
            bottom_stocks=bottom_stocks,
            sector_breakdown=sector_breakdown,
            model_metrics=model_metrics,
            run_name="Portfolio Analysis"
        )
        
        return insights.get('executive_summary', "Executive summary not available.")
    
    def generate_sector_analysis(
        self,
        scores: List[Dict[str, Any]],
        validation_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate sector analysis from stock scores.
        
        Args:
            scores: List of stock score dictionaries
            
        Returns:
            Sector analysis text
        """
        if not scores:
            return "No data available for sector analysis."
        
        # Sort by score and get top/bottom
        sorted_scores = sorted(scores, key=lambda x: x.get('score', 0), reverse=True)
        top_stocks = sorted_scores[:10]
        bottom_stocks = sorted_scores[-5:] if len(sorted_scores) > 5 else []
        
        # Build sector breakdown
        sector_breakdown = {}
        for s in scores:
            sector = s.get('sector', 'Other')
            if sector not in sector_breakdown:
                sector_breakdown[sector] = {'count': 0, 'avg_score': 0, 'scores': []}
            sector_breakdown[sector]['count'] += 1
            sector_breakdown[sector]['scores'].append(s.get('score', 0))
        
        for sector in sector_breakdown:
            scores_list = sector_breakdown[sector]['scores']
            sector_breakdown[sector]['avg_score'] = sum(scores_list) / len(scores_list) if scores_list else 0
            del sector_breakdown[sector]['scores']
        
        # Add validation warnings to context if present
        model_metrics = {'total_stocks': len(scores)}
        if validation_context:
            if validation_context.get('has_errors'):
                model_metrics['data_quality'] = 'ERRORS_DETECTED'
                model_metrics['data_errors'] = validation_context.get('errors', [])
            if validation_context.get('warnings'):
                model_metrics['data_quality'] = 'WARNINGS'
                model_metrics['data_warnings'] = validation_context.get('warnings', [])
        
        # Generate insights
        insights = self.generate_portfolio_insights(
            top_stocks=top_stocks,
            bottom_stocks=bottom_stocks,
            sector_breakdown=sector_breakdown,
            model_metrics=model_metrics,
            run_name="Portfolio Analysis"
        )
        
        return insights.get('sector_analysis', "Sector analysis not available.")
    
    def generate_recommendations(
        self,
        scores: List[Dict[str, Any]],
        risk_profile: str = "moderate",
    ) -> str:
        """
        Generate investment recommendations from stock scores.
        
        Args:
            scores: List of stock score dictionaries
            risk_profile: Risk profile ('conservative', 'moderate', 'aggressive')
            
        Returns:
            Recommendations text
        """
        if not scores:
            return "No data available for recommendations."
        
        # Sort by score and get top/bottom
        sorted_scores = sorted(scores, key=lambda x: x.get('score', 0), reverse=True)
        top_stocks = sorted_scores[:10]
        bottom_stocks = sorted_scores[-5:] if len(sorted_scores) > 5 else []
        
        # Build sector breakdown
        sector_breakdown = {}
        for s in scores:
            sector = s.get('sector', 'Other')
            if sector not in sector_breakdown:
                sector_breakdown[sector] = {'count': 0, 'avg_score': 0, 'scores': []}
            sector_breakdown[sector]['count'] += 1
            sector_breakdown[sector]['scores'].append(s.get('score', 0))
        
        for sector in sector_breakdown:
            scores_list = sector_breakdown[sector]['scores']
            sector_breakdown[sector]['avg_score'] = sum(scores_list) / len(scores_list) if scores_list else 0
            del sector_breakdown[sector]['scores']
        
        # Generate insights
        insights = self.generate_portfolio_insights(
            top_stocks=top_stocks,
            bottom_stocks=bottom_stocks,
            sector_breakdown=sector_breakdown,
            model_metrics={'total_stocks': len(scores), 'risk_profile': risk_profile},
            run_name=f"{risk_profile.title()} Portfolio Analysis"
        )
        
        recommendations = insights.get('recommendations', "")
        
        # Add risk-profile specific guidance
        profile_guidance = {
            'conservative': "\n\n**Conservative Approach:** Focus on high-quality, lower-volatility picks with strong fundamentals.",
            'moderate': "\n\n**Moderate Approach:** Balance growth potential with risk management across diversified sectors.",
            'aggressive': "\n\n**Aggressive Approach:** Prioritize high-conviction, high-growth opportunities with higher risk tolerance."
        }
        
        return recommendations + profile_guidance.get(risk_profile.lower(), "")
    
    def generate_risk_aware_insights(
        self,
        positions: List[Dict[str, Any]],
        risk_profile: Dict[str, Any],
        comparison: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Generate AI insights for risk-aware portfolio construction.
        
        Args:
            positions: List of positions with risk metrics (weight, vol, beta, etc.)
            risk_profile: Portfolio risk profile dict
            comparison: Optional comparison between equal-weight and risk-parity
            
        Returns:
            Dictionary with risk-focused insight sections
        """
        if not self.is_available:
            return self._generate_risk_fallback(positions, risk_profile)
        
        # Build context
        context = self._build_risk_context(positions, risk_profile, comparison)
        
        insights = {}
        
        # Risk-aware allocation rationale
        insights['allocation_rationale'] = self._generate_risk_section(
            "allocation_rationale", context
        )
        
        # Beta and volatility analysis
        insights['beta_analysis'] = self._generate_risk_section(
            "beta_analysis", context
        )
        
        # Position sizing recommendations
        insights['sizing_recommendations'] = self._generate_risk_section(
            "sizing_recommendations", context
        )
        
        return insights
    
    def _build_risk_context(
        self,
        positions: List[Dict],
        risk_profile: Dict,
        comparison: Optional[Dict] = None,
    ) -> str:
        """Build context string for risk-aware insights."""
        
        # Format positions
        pos_str = "\n".join([
            f"  {p['ticker']}: Weight={p.get('risk_weight', 0)*100:.1f}%, "
            f"Vol={p.get('volatility', 0)*100:.0f}%, Beta={p.get('beta', 1):.2f}, "
            f"Sector={p.get('sector', 'Unknown')}"
            for p in positions[:15]
        ])
        
        # Format risk profile
        profile_str = f"""
Portfolio Beta: {risk_profile.get('total_beta', 1.0):.2f}
Weighted Avg Volatility: {risk_profile.get('weighted_avg_vol', 0.20)*100:.1f}%
Est. Portfolio Volatility: {risk_profile.get('portfolio_vol_estimate', 0.20)*100:.1f}%
Concentration (HHI): {risk_profile.get('concentration_hhi', 0):.0f}
Effective Positions: {risk_profile.get('effective_n', 0):.1f}
Risk Tilt: {risk_profile.get('risk_tilt', 'Unknown')}
"""
        
        # Sector exposure
        sector_exp = risk_profile.get('sector_exposure', {})
        sector_str = "\n".join([
            f"  {sector}: {weight*100:.1f}%"
            for sector, weight in sorted(sector_exp.items(), key=lambda x: -x[1])
        ])
        
        # Beta exposure
        beta_exp = risk_profile.get('beta_exposure', {})
        beta_str = "\n".join([
            f"  {cat}: {weight*100:.1f}%"
            for cat, weight in beta_exp.items()
        ])
        
        # Comparison if available
        comparison_str = ""
        if comparison:
            comparison_str = f"""
EQUAL WEIGHT vs RISK PARITY COMPARISON:
Equal Weight Portfolio Beta: {comparison.get('ew_beta', 1.0):.2f}
Risk Parity Portfolio Beta: {comparison.get('rp_beta', 1.0):.2f}
Equal Weight Est. Vol: {comparison.get('ew_vol', 0.20)*100:.1f}%
Risk Parity Est. Vol: {comparison.get('rp_vol', 0.20)*100:.1f}%
Sharpe Improvement: {comparison.get('sharpe_improvement', 0)*100:.1f}%
"""
        
        context = f"""
RISK-AWARE PORTFOLIO ANALYSIS
=============================
Analysis Date: {datetime.now().strftime('%Y-%m-%d')}

PORTFOLIO RISK PROFILE:
{profile_str}

BETA EXPOSURE:
{beta_str}

SECTOR EXPOSURE:
{sector_str}

TOP POSITIONS (Risk-Adjusted):
{pos_str}

{comparison_str}

METHODOLOGY:
- Inverse volatility weighting reduces allocation to high-vol names
- Risk parity targets equal risk contribution from each position
- Sector caps prevent concentration (Nuclear ≤15%, Semis ≤20%, Tech ≤30%)
- Max single position weight: 10%
"""
        return context
    
    def _generate_risk_section(self, section_type: str, context: str) -> str:
        """Generate a specific risk-focused insight section."""
        
        prompts = {
            "allocation_rationale": """
Based on the risk-aware portfolio analysis below, explain the allocation rationale (2-3 paragraphs):
1. Why risk parity/inverse-vol weighting was applied
2. How it changes the portfolio compared to equal/score weighting
3. The risk-return tradeoff implications
4. Whether this creates a better risk-adjusted portfolio

Be specific about which stocks were down-weighted (high vol) vs up-weighted (low vol).
""",
            "beta_analysis": """
Based on the portfolio analysis below, provide a beta and market exposure analysis:
1. Is this portfolio running a high-beta equity tilt?
2. How does the beta breakdown affect expected performance in bull/bear markets?
3. Are there sector concentrations that amplify systematic risk?
4. Recommendations to achieve a more balanced beta profile if needed

Include specific sector weights and their impact on overall beta.
""",
            "sizing_recommendations": """
Based on the portfolio analysis below, provide specific position sizing recommendations:
1. Which positions should be increased/decreased based on risk metrics?
2. Specific percentage adjustments for top holdings
3. Sector rebalancing needed to match "balanced" risk intent
4. Stop-loss levels based on volatility
5. Rebalancing triggers and frequency

Be concrete with numbers and percentages.
"""
        }
        
        prompt = prompts.get(section_type, prompts["allocation_rationale"])
        full_prompt = f"{prompt}\n\n{context}"
        
        try:
            response = self._model.generate_content(
                full_prompt,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 1000,
                }
            )
            return response.text.strip()
        except Exception as e:
            return f"[Risk insight generation failed: {e}]"
    
    def _generate_risk_fallback(
        self,
        positions: List[Dict],
        risk_profile: Dict,
    ) -> Dict[str, str]:
        """Generate basic risk insights without AI."""
        
        total_beta = risk_profile.get('total_beta', 1.0)
        risk_tilt = risk_profile.get('risk_tilt', 'Unknown')
        
        allocation = f"""
## Allocation Rationale

The portfolio uses **inverse volatility weighting** to reduce risk concentration.
Higher volatility stocks receive lower weights to ensure no single position 
dominates portfolio risk.

**Current Risk Profile:**
- Portfolio Beta: {total_beta:.2f}
- Risk Tilt: {risk_tilt}

*Enable AI insights for detailed analysis.*
"""
        
        beta_analysis = f"""
## Beta Analysis

Portfolio Beta: **{total_beta:.2f}**

{'⚠️ High beta exposure (>1.15) indicates aggressive market positioning.' if total_beta > 1.15 else ''}
{'✅ Balanced beta exposure.' if 0.85 <= total_beta <= 1.15 else ''}
{'🛡️ Defensive positioning (beta < 0.85).' if total_beta < 0.85 else ''}

*Enable AI for detailed beta and sector analysis.*
"""
        
        return {
            'allocation_rationale': allocation,
            'beta_analysis': beta_analysis,
            'sizing_recommendations': "Detailed sizing recommendations require AI insights to be enabled.",
        }
    
    def _generate_stock_fallback(self, ticker: str, score_data: Dict) -> str:
        """Generate basic stock insight without AI."""
        score = score_data.get('score') or 0
        rsi = score_data.get('rsi') or 50
        ret_21d_raw = score_data.get('return_21d') or 0
        ret_21d = ret_21d_raw * 100
        
        # Simple rule-based assessment
        if score > 0.7:
            rating = "STRONG BUY"
            outlook = "highly favorable"
        elif score > 0.5:
            rating = "BUY"
            outlook = "positive"
        elif score > 0.3:
            rating = "HOLD"
            outlook = "neutral"
        else:
            rating = "AVOID"
            outlook = "unfavorable"
        
        if rsi > 70:
            rsi_comment = "RSI indicates overbought conditions - consider waiting for pullback."
        elif rsi < 30:
            rsi_comment = "RSI indicates oversold conditions - potential buying opportunity."
        else:
            rsi_comment = "RSI is in neutral territory."
        
        return f"""
**{ticker} Analysis**

Overall Score: {score:.4f} | Rating: {rating}

The stock shows {outlook} positioning based on our multi-factor analysis. 
Recent 21-day return of {ret_21d:+.1f}% reflects current momentum.

Technical: {rsi_comment}

*Enable AI insights for detailed analysis and specific recommendations.*
"""


def generate_ai_report_section(
    top_stocks: List[Dict],
    bottom_stocks: List[Dict],
    sector_breakdown: Dict[str, Dict],
    model_metrics: Dict[str, float],
    run_name: str = "Analysis",
) -> str:
    """
    Convenience function to generate AI insights for a report.
    
    Returns a formatted markdown string with all insights.
    """
    generator = AIInsightsGenerator()
    
    insights = generator.generate_portfolio_insights(
        top_stocks=top_stocks,
        bottom_stocks=bottom_stocks,
        sector_breakdown=sector_breakdown,
        model_metrics=model_metrics,
        run_name=run_name,
    )
    
    # Format as markdown
    report = f"""
# 🤖 AI-Powered Analysis Insights

*Generated by Gemini AI on {datetime.now().strftime('%Y-%m-%d %H:%M')}*

---

## 📋 Executive Summary

{insights.get('executive_summary', 'Not available')}

---

## 🏆 Top Picks Analysis

{insights.get('top_picks_analysis', 'Not available')}

---

## 📊 Sector Analysis

{insights.get('sector_analysis', 'Not available')}

---

## ⚠️ Risk Assessment

{insights.get('risk_assessment', 'Not available')}

---

## 💡 Recommendations

{insights.get('recommendations', 'Not available')}

---

*Disclaimer: This analysis is generated by AI for informational purposes only. 
Not financial advice. Always do your own research before investing.*
"""
    
    return report


if __name__ == "__main__":
    # Test the insights generator
    print("Testing AI Insights Generator...")
    
    generator = AIInsightsGenerator()
    print(f"AI Available: {generator.is_available}")
    
    # Sample data
    test_stocks = [
        {"ticker": "NVDA", "score": 0.85, "tech_score": 0.9, "fund_score": 0.8, "sent_score": 0.7, "rsi": 55, "return_21d": 0.05},
        {"ticker": "AAPL", "score": 0.75, "tech_score": 0.8, "fund_score": 0.7, "sent_score": 0.6, "rsi": 45, "return_21d": 0.02},
        {"ticker": "MSFT", "score": 0.70, "tech_score": 0.7, "fund_score": 0.75, "sent_score": 0.65, "rsi": 50, "return_21d": 0.01},
    ]
    
    test_sectors = {
        "Technology": {"score": 0.75, "count": 10},
        "Healthcare": {"score": 0.60, "count": 5},
        "Financials": {"score": 0.55, "count": 6},
    }
    
    test_metrics = {
        "spearman_corr": 0.18,
        "hit_rate": 0.62,
        "sharpe_ratio": 0.55,
    }
    
    if generator.is_available:
        print("\nGenerating insights...")
        insights = generator.generate_portfolio_insights(
            top_stocks=test_stocks,
            bottom_stocks=test_stocks[-2:],
            sector_breakdown=test_sectors,
            model_metrics=test_metrics,
        )
        
        print("\n" + "="*60)
        print("EXECUTIVE SUMMARY:")
        print("="*60)
        print(insights.get('executive_summary', 'N/A')[:500] + "...")
    else:
        print("AI not available - using fallback insights")
