"""
Analysis Module
===============
Provides vertical (within-sector) and horizontal (across-sector) analysis
for rigorous numeric stock selection.

Gemini commentary is OPTIONAL and used only for explanation, not decision-making.
"""

from .domain_analysis import (
    AnalysisConfig,
    DomainAnalyzer,
    VerticalResult,
    HorizontalResult,
)

from .gemini_commentary import (
    generate_portfolio_commentary,
    generate_comparison_commentary,
    generate_risk_commentary,
    generate_portfolio_recommendations,
    save_commentary_to_file,
    save_recommendations_to_file,
)

__all__ = [
    # Domain Analysis (numeric, primary)
    'AnalysisConfig',
    'DomainAnalyzer',
    'VerticalResult',
    'HorizontalResult',
    # Gemini Commentary (optional, secondary)
    'generate_portfolio_commentary',
    'generate_comparison_commentary',
    'generate_risk_commentary',
    'generate_portfolio_recommendations',
    'save_commentary_to_file',
    'save_recommendations_to_file',
]
