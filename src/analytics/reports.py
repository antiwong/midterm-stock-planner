"""
Report Generator
================
Generate various report formats from analysis runs.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import markdown

from .models import get_db, Run, StockScore
from .ai_insights import AIInsightsGenerator

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates reports from analysis runs."""
    
    def __init__(self, db_path: str = "data/analysis.db", enable_ai_insights: bool = True):
        self.db = get_db(db_path)
        self.enable_ai_insights = enable_ai_insights
        self._ai_generator = AIInsightsGenerator() if enable_ai_insights else None
    
    def _format_metric(self, key: str, value: Any) -> str:
        """Format a metric value for display."""
        if value is None:
            return "N/A"
        if isinstance(value, float):
            if 'return' in key or 'rate' in key or 'drawdown' in key:
                return f"{value*100:.2f}%"
            elif 'ratio' in key or 'sharpe' in key:
                return f"{value:.3f}"
            else:
                return f"{value:.4f}"
        return str(value)
    
    def _prepare_ai_context(self, run: Run, scores: List[StockScore]) -> Dict[str, Any]:
        """Prepare data context for AI insights generation."""
        # Convert scores to dictionaries with all relevant fields
        top_stocks = []
        for s in scores[:15]:
            features = s.get_features() if hasattr(s, 'get_features') else {}
            top_stocks.append({
                'ticker': s.ticker,
                'score': s.score or 0,
                'tech_score': s.tech_score or 0,
                'fund_score': s.fund_score or 0,
                'sent_score': s.sent_score or 0,
                'rsi': features.get('rsi', s.rsi or 50),
                'return_21d': features.get('return_21d', 0),
                'return_63d': features.get('return_63d', 0),
                'volatility': features.get('volatility', 0),
                'sector': s.sector or 'Unknown',
            })
        
        bottom_stocks = []
        for s in scores[-5:]:
            features = s.get_features() if hasattr(s, 'get_features') else {}
            bottom_stocks.append({
                'ticker': s.ticker,
                'score': s.score or 0,
                'return_21d': features.get('return_21d', 0),
            })
        
        # Build sector breakdown
        sector_scores = {}
        for s in scores:
            sector = s.sector or 'Unknown'
            if sector not in sector_scores:
                sector_scores[sector] = {'scores': [], 'count': 0}
            sector_scores[sector]['scores'].append(s.score or 0)
            sector_scores[sector]['count'] += 1
        
        sector_breakdown = {
            sector: {
                'score': sum(data['scores']) / len(data['scores']) if data['scores'] else 0,
                'count': data['count']
            }
            for sector, data in sector_scores.items()
        }
        
        # Model metrics
        model_metrics = {
            'spearman_corr': run.spearman_corr or 0,
            'hit_rate': run.hit_rate or 0,
            'sharpe_ratio': run.sharpe_ratio or 0,
            'total_return': run.total_return or 0,
            'win_rate': run.win_rate or 0,
            'max_drawdown': run.max_drawdown or 0,
        }
        
        return {
            'top_stocks': top_stocks,
            'bottom_stocks': bottom_stocks,
            'sector_breakdown': sector_breakdown,
            'model_metrics': model_metrics,
        }
    
    def _generate_ai_insights(self, run: Run, scores: List[StockScore]) -> Dict[str, str]:
        """Generate AI insights for the analysis."""
        if not self._ai_generator or not self._ai_generator.is_available:
            return {}
        
        try:
            context = self._prepare_ai_context(run, scores)
            insights = self._ai_generator.generate_portfolio_insights(
                top_stocks=context['top_stocks'],
                bottom_stocks=context['bottom_stocks'],
                sector_breakdown=context['sector_breakdown'],
                model_metrics=context['model_metrics'],
                run_name=run.name or run.run_id,
            )
            return insights
        except Exception as e:
            logger.error(f"Failed to generate AI insights: {e}")
            return {}
    
    def generate_report(
        self,
        run_id: str,
        output_dir: Optional[Path] = None,
        format: str = "all",
        include_ai_insights: bool = True,
    ) -> Dict[str, Path]:
        """Generate reports for a run.
        
        Args:
            run_id: The run ID to generate reports for
            output_dir: Output directory path
            format: Report format - "json", "markdown", "md", "html", or "all"
            include_ai_insights: Whether to include AI-generated insights
            
        Returns:
            Dictionary mapping format to generated file path
        """
        session = self.db.get_session()
        try:
            run = session.query(Run).filter_by(run_id=run_id).first()
            if not run:
                logger.error(f"Run {run_id} not found")
                return {}
            
            scores = session.query(StockScore).filter_by(run_id=run_id).order_by(StockScore.rank).all()
            
            if output_dir is None:
                output_dir = Path(f"output/{run_id}")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate AI insights if enabled
            ai_insights = {}
            if include_ai_insights and self.enable_ai_insights and len(scores) > 0:
                logger.info("Generating AI-powered insights...")
                ai_insights = self._generate_ai_insights(run, scores)
                if ai_insights:
                    logger.info(f"Generated {len(ai_insights)} AI insight sections")
                else:
                    logger.warning("AI insights generation returned empty results")
            
            generated = {}
            
            if format in ("json", "all"):
                path = self._generate_json(run, scores, output_dir, ai_insights)
                generated["json"] = path
            
            if format in ("markdown", "md", "all"):
                path = self._generate_markdown(run, scores, output_dir, ai_insights)
                generated["markdown"] = path
            
            if format in ("html", "all"):
                path = self._generate_html(run, scores, output_dir, ai_insights)
                generated["html"] = path
            
            return generated
        finally:
            session.close()
    
    def _generate_json(self, run: Run, scores: List[StockScore], output_dir: Path, ai_insights: Optional[Dict[str, str]] = None) -> Path:
        """Generate JSON report."""
        path = output_dir / "report.json"
        
        data = run.to_dict()
        data['scores'] = [s.to_dict() for s in scores]
        
        # Include AI insights if available
        if ai_insights:
            data['ai_insights'] = ai_insights
            data['ai_insights_generated'] = True
        else:
            data['ai_insights_generated'] = False
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        return path
    
    def _generate_markdown(self, run: Run, scores: List[StockScore], output_dir: Path, ai_insights: Optional[Dict[str, str]] = None) -> Path:
        """Generate Markdown report."""
        path = output_dir / "report.md"
        
        lines = []
        lines.append(f"# {run.name or run.run_id}")
        lines.append("")
        lines.append(f"**Run ID:** `{run.run_id}`")
        lines.append(f"**Type:** {run.run_type}")
        lines.append(f"**Status:** {run.status}")
        lines.append(f"**Created:** {run.created_at}")
        lines.append("")
        
        if run.description:
            lines.append(f"> {run.description}")
            lines.append("")
        
        # AI Executive Summary (at the top for visibility)
        if ai_insights and ai_insights.get('executive_summary'):
            lines.append("---")
            lines.append("")
            lines.append("## 🤖 AI Executive Summary")
            lines.append("")
            lines.append(ai_insights['executive_summary'])
            lines.append("")
        
        # Metrics
        lines.append("## 📊 Performance Metrics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        
        metrics = [
            ('Total Return', run.total_return),
            ('Sharpe Ratio', run.sharpe_ratio),
            ('Max Drawdown', run.max_drawdown),
            ('Win Rate', run.win_rate),
            ('Hit Rate', run.hit_rate),
            ('Spearman Correlation', run.spearman_corr),
            ('Stocks Analyzed', run.universe_count),
        ]
        
        for name, value in metrics:
            if value is not None:
                formatted = self._format_metric(name.lower(), value)
                lines.append(f"| {name} | {formatted} |")
        
        lines.append("")
        
        # Top stocks
        if scores:
            lines.append("## 🏆 Top 20 Stocks")
            lines.append("")
            lines.append("| Rank | Ticker | Score | Tech | Fund | Sent |")
            lines.append("|------|--------|-------|------|------|------|")
            
            for s in scores[:20]:
                tech = f"{s.tech_score:.3f}" if s.tech_score else "-"
                fund = f"{s.fund_score:.3f}" if s.fund_score else "-"
                sent = f"{s.sent_score:.3f}" if s.sent_score else "-"
                lines.append(f"| {s.rank} | {s.ticker} | {s.score:.4f} | {tech} | {fund} | {sent} |")
            
            lines.append("")
        
        # AI Top Picks Analysis
        if ai_insights and ai_insights.get('top_picks_analysis'):
            lines.append("---")
            lines.append("")
            lines.append("## 🎯 AI Top Picks Analysis")
            lines.append("")
            lines.append(ai_insights['top_picks_analysis'])
            lines.append("")
        
        # AI Sector Analysis
        if ai_insights and ai_insights.get('sector_analysis'):
            lines.append("---")
            lines.append("")
            lines.append("## 📈 AI Sector Analysis")
            lines.append("")
            lines.append(ai_insights['sector_analysis'])
            lines.append("")
        
        # AI Risk Assessment
        if ai_insights and ai_insights.get('risk_assessment'):
            lines.append("---")
            lines.append("")
            lines.append("## ⚠️ AI Risk Assessment")
            lines.append("")
            lines.append(ai_insights['risk_assessment'])
            lines.append("")
        
        # AI Recommendations
        if ai_insights and ai_insights.get('recommendations'):
            lines.append("---")
            lines.append("")
            lines.append("## 💡 AI Investment Recommendations")
            lines.append("")
            lines.append(ai_insights['recommendations'])
            lines.append("")
        
        # Config
        config = run.get_config()
        if config:
            lines.append("---")
            lines.append("")
            lines.append("## ⚙️ Configuration")
            lines.append("")
            lines.append("<details>")
            lines.append("<summary>Click to expand configuration</summary>")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(config, indent=2))
            lines.append("```")
            lines.append("</details>")
            lines.append("")
        
        # Disclaimer
        if ai_insights:
            lines.append("---")
            lines.append("")
            lines.append("### ⚖️ Disclaimer")
            lines.append("")
            lines.append("*The AI-generated insights are for informational purposes only and do not constitute financial advice. ")
            lines.append("Always conduct your own research and consult with qualified financial advisors before making investment decisions.*")
            lines.append("")
        
        # Footer
        lines.append("---")
        lines.append(f"*Generated at {datetime.now().isoformat()}*")
        
        with open(path, 'w') as f:
            f.write('\n'.join(lines))
        
        return path
    
    def _generate_html(self, run: Run, scores: List[StockScore], output_dir: Path, ai_insights: Optional[Dict[str, str]] = None) -> Path:
        """Generate HTML report with AI insights."""
        path = output_dir / "report.html"
        
        # Convert markdown insights to HTML
        def md_to_html(text: str) -> str:
            if not text:
                return ""
            try:
                return markdown.markdown(text, extensions=['tables', 'fenced_code'])
            except:
                # Fallback: basic conversion
                return text.replace('\n\n', '</p><p>').replace('\n', '<br>')
        
        # Build HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{run.name or run.run_id} - Analysis Report</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
        
        :root {{
            --bg-dark: #0d1117;
            --bg-card: #161b22;
            --bg-card-hover: #1c2128;
            --accent: #238636;
            --accent-light: #2ea043;
            --highlight: #58a6ff;
            --warning: #d29922;
            --danger: #f85149;
            --text: #e6edf3;
            --text-muted: #8b949e;
            --border: #30363d;
            --gradient-1: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --gradient-2: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            --gradient-3: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-dark);
            color: var(--text);
            line-height: 1.7;
            font-size: 15px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        header {{
            text-align: center;
            padding: 4rem 2rem;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            border-radius: 20px;
            margin-bottom: 2rem;
            border: 1px solid var(--border);
            position: relative;
            overflow: hidden;
        }}
        
        header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
            opacity: 0.5;
        }}
        
        header h1 {{
            font-size: 2.8rem;
            margin-bottom: 0.75rem;
            font-weight: 700;
            background: linear-gradient(135deg, #fff 0%, #a8b2d1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            position: relative;
        }}
        
        header p {{
            color: var(--text-muted);
            font-size: 1rem;
            position: relative;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2rem;
        }}
        
        .metric-card {{
            background: var(--bg-card);
            padding: 1.75rem;
            border-radius: 16px;
            text-align: center;
            border: 1px solid var(--border);
            transition: all 0.3s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-4px);
            border-color: var(--highlight);
            box-shadow: 0 8px 30px rgba(88, 166, 255, 0.15);
        }}
        
        .metric-card .value {{
            font-size: 2.2rem;
            font-weight: 700;
            background: var(--gradient-3);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .metric-card .label {{
            color: var(--text-muted);
            font-size: 0.85rem;
            margin-top: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .section {{
            background: var(--bg-card);
            padding: 2rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            border: 1px solid var(--border);
        }}
        
        .section h2 {{
            margin-bottom: 1.5rem;
            padding-bottom: 0.75rem;
            border-bottom: 2px solid var(--border);
            font-size: 1.5rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        
        .section h2 .icon {{
            font-size: 1.3rem;
        }}
        
        .ai-section {{
            background: linear-gradient(135deg, rgba(88, 166, 255, 0.05) 0%, rgba(35, 134, 54, 0.05) 100%);
            border: 1px solid rgba(88, 166, 255, 0.2);
        }}
        
        .ai-section h2 {{
            color: var(--highlight);
        }}
        
        .ai-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: linear-gradient(135deg, var(--highlight) 0%, var(--accent) 100%);
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .ai-content {{
            font-size: 1rem;
            line-height: 1.8;
        }}
        
        .ai-content p {{
            margin-bottom: 1rem;
        }}
        
        .ai-content h3, .ai-content h4 {{
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
            color: var(--highlight);
        }}
        
        .ai-content ul, .ai-content ol {{
            margin-left: 1.5rem;
            margin-bottom: 1rem;
        }}
        
        .ai-content li {{
            margin-bottom: 0.5rem;
        }}
        
        .ai-content strong {{
            color: var(--text);
        }}
        
        .ai-content code {{
            background: var(--bg-dark);
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9em;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }}
        
        th, td {{
            padding: 1rem 1.25rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        
        th {{
            background: var(--bg-dark);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.8rem;
            letter-spacing: 0.5px;
            color: var(--text-muted);
        }}
        
        tr:hover {{
            background: var(--bg-card-hover);
        }}
        
        .rank-1 {{ color: #ffd700; font-weight: 700; }}
        .rank-2 {{ color: #c0c0c0; font-weight: 600; }}
        .rank-3 {{ color: #cd7f32; font-weight: 600; }}
        
        .positive {{ color: var(--accent-light); }}
        .negative {{ color: var(--danger); }}
        
        .score-bar {{
            display: inline-block;
            height: 6px;
            background: linear-gradient(90deg, var(--highlight) 0%, var(--accent) 100%);
            border-radius: 3px;
            margin-left: 0.5rem;
        }}
        
        .ticker {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            color: var(--highlight);
        }}
        
        .nav-tabs {{
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        }}
        
        .nav-tab {{
            padding: 0.75rem 1.5rem;
            background: var(--bg-dark);
            border: 1px solid var(--border);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            font-weight: 500;
        }}
        
        .nav-tab:hover, .nav-tab.active {{
            background: var(--highlight);
            color: var(--bg-dark);
            border-color: var(--highlight);
        }}
        
        .disclaimer {{
            background: rgba(210, 153, 34, 0.1);
            border: 1px solid rgba(210, 153, 34, 0.3);
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 2rem;
            font-size: 0.9rem;
            color: var(--warning);
        }}
        
        .disclaimer-title {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }}
        
        footer {{
            text-align: center;
            padding: 3rem 2rem;
            color: var(--text-muted);
            font-size: 0.9rem;
            border-top: 1px solid var(--border);
            margin-top: 2rem;
        }}
        
        footer a {{
            color: var(--highlight);
            text-decoration: none;
        }}
        
        @media (max-width: 768px) {{
            .container {{ padding: 1rem; }}
            header h1 {{ font-size: 1.8rem; }}
            header {{ padding: 2rem 1rem; }}
            .metrics-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .nav-tabs {{ flex-direction: column; }}
            table {{ font-size: 0.85rem; }}
            th, td {{ padding: 0.75rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📈 {run.name or 'Stock Analysis Report'}</h1>
            <p>Run ID: <code style="background: rgba(255,255,255,0.1); padding: 0.2rem 0.5rem; border-radius: 4px;">{run.run_id}</code></p>
            <p style="margin-top: 0.5rem;">{run.run_type.title()} Analysis • {run.status.upper()} • {run.created_at.strftime('%B %d, %Y at %H:%M') if run.created_at else 'N/A'}</p>
        </header>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="value">{self._format_metric('return', run.total_return) if run.total_return else 'N/A'}</div>
                <div class="label">Total Return</div>
            </div>
            <div class="metric-card">
                <div class="value">{f'{run.sharpe_ratio:.2f}' if run.sharpe_ratio else 'N/A'}</div>
                <div class="label">Sharpe Ratio</div>
            </div>
            <div class="metric-card">
                <div class="value">{self._format_metric('rate', run.win_rate) if run.win_rate else 'N/A'}</div>
                <div class="label">Win Rate</div>
            </div>
            <div class="metric-card">
                <div class="value">{self._format_metric('rate', run.hit_rate) if run.hit_rate else 'N/A'}</div>
                <div class="label">Hit Rate</div>
            </div>
            <div class="metric-card">
                <div class="value">{run.universe_count or len(scores)}</div>
                <div class="label">Stocks Analyzed</div>
            </div>
            <div class="metric-card">
                <div class="value">{f'{run.spearman_corr:.3f}' if run.spearman_corr else 'N/A'}</div>
                <div class="label">Spearman Corr</div>
            </div>
        </div>
"""
        
        # AI Executive Summary
        if ai_insights and ai_insights.get('executive_summary'):
            html += f"""
        <div class="section ai-section">
            <h2><span class="icon">🤖</span> AI Executive Summary <span class="ai-badge">Powered by Gemini</span></h2>
            <div class="ai-content">
                {md_to_html(ai_insights['executive_summary'])}
            </div>
        </div>
"""
        
        # Top Stocks Table
        html += """
        <div class="section">
            <h2><span class="icon">🏆</span> Top Ranked Stocks</h2>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Ticker</th>
                        <th>Score</th>
                        <th>Technical</th>
                        <th>Fundamental</th>
                        <th>Sentiment</th>
                        <th>RSI</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for s in scores[:30]:
            rank_class = f"rank-{s.rank}" if s.rank and s.rank <= 3 else ""
            score_width = int((s.score or 0) * 100)
            
            html += f"""
                    <tr>
                        <td class="{rank_class}">#{s.rank or '-'}</td>
                        <td class="ticker">{s.ticker}</td>
                        <td>
                            {f'{s.score:.4f}' if s.score else '-'}
                            <div class="score-bar" style="width: {score_width}px;"></div>
                        </td>
                        <td>{f'{s.tech_score:.3f}' if s.tech_score else '-'}</td>
                        <td>{f'{s.fund_score:.3f}' if s.fund_score else '-'}</td>
                        <td>{f'{s.sent_score:.3f}' if s.sent_score else '-'}</td>
                        <td>{f'{s.rsi:.0f}' if s.rsi else '-'}</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
"""
        
        # AI Top Picks Analysis
        if ai_insights and ai_insights.get('top_picks_analysis'):
            html += f"""
        <div class="section ai-section">
            <h2><span class="icon">🎯</span> AI Top Picks Analysis</h2>
            <div class="ai-content">
                {md_to_html(ai_insights['top_picks_analysis'])}
            </div>
        </div>
"""
        
        # AI Sector Analysis
        if ai_insights and ai_insights.get('sector_analysis'):
            html += f"""
        <div class="section ai-section">
            <h2><span class="icon">📊</span> AI Sector Analysis</h2>
            <div class="ai-content">
                {md_to_html(ai_insights['sector_analysis'])}
            </div>
        </div>
"""
        
        # AI Risk Assessment
        if ai_insights and ai_insights.get('risk_assessment'):
            html += f"""
        <div class="section ai-section">
            <h2><span class="icon">⚠️</span> AI Risk Assessment</h2>
            <div class="ai-content">
                {md_to_html(ai_insights['risk_assessment'])}
            </div>
        </div>
"""
        
        # AI Recommendations
        if ai_insights and ai_insights.get('recommendations'):
            html += f"""
        <div class="section ai-section">
            <h2><span class="icon">💡</span> AI Investment Recommendations</h2>
            <div class="ai-content">
                {md_to_html(ai_insights['recommendations'])}
            </div>
        </div>
"""
        
        # Disclaimer
        if ai_insights:
            html += """
        <div class="disclaimer">
            <div class="disclaimer-title">⚖️ Important Disclaimer</div>
            <p>The AI-generated insights in this report are for informational purposes only and do not constitute financial advice. 
            Past performance is not indicative of future results. Always conduct your own research and consult with qualified 
            financial advisors before making investment decisions. The AI model may produce errors or inaccuracies.</p>
        </div>
"""
        
        # Footer
        html += f"""
        <footer>
            <p>Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Midterm Stock Planner • AI-Powered Analysis Platform</p>
        </footer>
    </div>
</body>
</html>
"""
        
        with open(path, 'w') as f:
            f.write(html)
        
        return path
