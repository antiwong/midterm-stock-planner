"""
Extended Database Models for Analysis Results
============================================
SQLAlchemy models for storing comprehensive analysis results, AI insights,
and historical tracking.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, 
    Text, ForeignKey, Boolean, Index, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

# Import Base from models to ensure consistency
try:
    from .models import Base
except ImportError:
    # Fallback if models not available
    Base = declarative_base()


class AnalysisResult(Base):
    """Stores comprehensive analysis results for a run."""
    __tablename__ = 'analysis_results'
    
    id = Column(Integer, primary_key=True)
    run_id = Column(String(50), ForeignKey('runs.run_id'), nullable=False, index=True)
    
    # Analysis type
    analysis_type = Column(String(50), nullable=False)  # attribution, benchmark, factor_exposure, etc.
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Results as JSON
    results_json = Column(Text, nullable=False)  # Full analysis results
    
    # Summary metrics (for quick queries)
    summary_json = Column(Text)  # Key metrics extracted for quick access
    
    # Status
    status = Column(String(20), default='completed')  # completed, failed, in_progress
    error_message = Column(Text)
    
    __table_args__ = (
        Index('idx_analysis_run_type', 'run_id', 'analysis_type'),
        Index('idx_analysis_created', 'created_at'),
    )
    
    def get_results(self) -> Dict:
        """Get full analysis results."""
        return json.loads(self.results_json) if self.results_json else {}
    
    def set_results(self, results: Dict):
        """Set analysis results."""
        self.results_json = json.dumps(results, default=str)
    
    def get_summary(self) -> Dict:
        """Get summary metrics."""
        return json.loads(self.summary_json) if self.summary_json else {}
    
    def set_summary(self, summary: Dict):
        """Set summary metrics."""
        self.summary_json = json.dumps(summary, default=str)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'run_id': self.run_id,
            'analysis_type': self.analysis_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'status': self.status,
            'results': self.get_results(),
            'summary': self.get_summary(),
            'error_message': self.error_message,
        }


class AIInsight(Base):
    """Stores AI-generated insights and recommendations."""
    __tablename__ = 'ai_insights'
    
    id = Column(Integer, primary_key=True)
    run_id = Column(String(50), ForeignKey('runs.run_id'), nullable=False, index=True)
    
    # Insight type
    insight_type = Column(String(50), nullable=False)  # portfolio_commentary, recommendations, sector_analysis, etc.
    
    # Content
    content = Column(Text, nullable=False)  # Main content (markdown or text)
    content_json = Column(Text)  # Structured data (for recommendations, etc.)
    
    # Metadata
    model = Column(String(50), default='gemini')  # Which AI model was used
    model_version = Column(String(20))  # Model version/parameters
    prompt_hash = Column(String(64))  # Hash of prompt for deduplication
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    
    # Context used for generation
    context_json = Column(Text)  # What data was used to generate this
    
    # Status
    status = Column(String(20), default='completed')  # completed, failed, cached
    error_message = Column(Text)
    
    # Relationships
    run = relationship("Run", backref="ai_insights")
    
    __table_args__ = (
        Index('idx_ai_insight_run_type', 'run_id', 'insight_type'),
        Index('idx_ai_insight_created', 'created_at'),
        Index('idx_ai_insight_prompt', 'prompt_hash'),
    )
    
    def get_content_json(self) -> Dict:
        """Get structured content."""
        return json.loads(self.content_json) if self.content_json else {}
    
    def set_content_json(self, data: Dict):
        """Set structured content."""
        self.content_json = json.dumps(data, default=str)
    
    def get_context(self) -> Dict:
        """Get generation context."""
        return json.loads(self.context_json) if self.context_json else {}
    
    def set_context(self, context: Dict):
        """Set generation context."""
        self.context_json = json.dumps(context, default=str)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'run_id': self.run_id,
            'insight_type': self.insight_type,
            'content': self.content,
            'content_json': self.get_content_json(),
            'model': self.model,
            'model_version': self.model_version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'context': self.get_context(),
            'status': self.status,
            'error_message': self.error_message,
        }


class Recommendation(Base):
    """Stores investment recommendations with tracking."""
    __tablename__ = 'recommendations'
    
    id = Column(Integer, primary_key=True)
    run_id = Column(String(50), ForeignKey('runs.run_id'), nullable=False, index=True)
    
    # Recommendation details
    ticker = Column(String(20), nullable=False, index=True)
    action = Column(String(20), nullable=False)  # BUY, SELL, HOLD, AVOID
    recommendation_date = Column(DateTime, nullable=False, index=True)
    
    # Reasoning
    reason = Column(Text)
    confidence = Column(Float)  # 0-1 confidence score
    target_price = Column(Float)
    stop_loss = Column(Float)
    time_horizon = Column(String(20))  # short, medium, long
    
    # Context
    current_price = Column(Float)
    score = Column(Float)
    sector = Column(String(100))
    
    # Tracking (updated over time)
    actual_return = Column(Float)  # Actual return if action was taken
    hit_target = Column(Boolean)  # Did it hit target price?
    hit_stop_loss = Column(Boolean)  # Did it hit stop loss?
    tracking_updated_at = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    source = Column(String(50), default='ai')  # ai, manual, rule_based
    
    __table_args__ = (
        Index('idx_recommendation_ticker_date', 'ticker', 'recommendation_date'),
        Index('idx_recommendation_action', 'action'),
    )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'run_id': self.run_id,
            'ticker': self.ticker,
            'action': self.action,
            'recommendation_date': self.recommendation_date.isoformat() if self.recommendation_date else None,
            'reason': self.reason,
            'confidence': self.confidence,
            'target_price': self.target_price,
            'stop_loss': self.stop_loss,
            'time_horizon': self.time_horizon,
            'current_price': self.current_price,
            'score': self.score,
            'sector': self.sector,
            'actual_return': self.actual_return,
            'hit_target': self.hit_target,
            'hit_stop_loss': self.hit_stop_loss,
            'tracking_updated_at': self.tracking_updated_at.isoformat() if self.tracking_updated_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'source': self.source,
        }


class BenchmarkComparison(Base):
    """Stores benchmark comparison results."""
    __tablename__ = 'benchmark_comparisons'
    
    id = Column(Integer, primary_key=True)
    run_id = Column(String(50), ForeignKey('runs.run_id'), nullable=False, index=True)
    
    # Benchmark details
    benchmark_symbol = Column(String(20), nullable=False)  # SPY, QQQ, etc.
    benchmark_name = Column(String(100))
    
    # Comparison period
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Portfolio metrics
    portfolio_return = Column(Float, nullable=False)
    portfolio_volatility = Column(Float)
    portfolio_sharpe = Column(Float)
    portfolio_max_drawdown = Column(Float)
    
    # Benchmark metrics
    benchmark_return = Column(Float, nullable=False)
    benchmark_volatility = Column(Float)
    benchmark_sharpe = Column(Float)
    benchmark_max_drawdown = Column(Float)
    
    # Relative metrics
    alpha = Column(Float)  # Excess return
    beta = Column(Float)  # Market sensitivity
    tracking_error = Column(Float)
    information_ratio = Column(Float)
    up_capture = Column(Float)  # % of benchmark upside captured
    down_capture = Column(Float)  # % of benchmark downside captured
    
    # Additional metrics as JSON
    metrics_json = Column(Text)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    
    __table_args__ = (
        Index('idx_benchmark_run_symbol', 'run_id', 'benchmark_symbol'),
        Index('idx_benchmark_dates', 'start_date', 'end_date'),
    )
    
    def get_metrics(self) -> Dict:
        """Get additional metrics."""
        return json.loads(self.metrics_json) if self.metrics_json else {}
    
    def set_metrics(self, metrics: Dict):
        """Set additional metrics."""
        self.metrics_json = json.dumps(metrics, default=str)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'run_id': self.run_id,
            'benchmark_symbol': self.benchmark_symbol,
            'benchmark_name': self.benchmark_name,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'portfolio_return': self.portfolio_return,
            'portfolio_volatility': self.portfolio_volatility,
            'portfolio_sharpe': self.portfolio_sharpe,
            'portfolio_max_drawdown': self.portfolio_max_drawdown,
            'benchmark_return': self.benchmark_return,
            'benchmark_volatility': self.benchmark_volatility,
            'benchmark_sharpe': self.benchmark_sharpe,
            'benchmark_max_drawdown': self.benchmark_max_drawdown,
            'alpha': self.alpha,
            'beta': self.beta,
            'tracking_error': self.tracking_error,
            'information_ratio': self.information_ratio,
            'up_capture': self.up_capture,
            'down_capture': self.down_capture,
            'metrics': self.get_metrics(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class FactorExposure(Base):
    """Stores factor exposure analysis results."""
    __tablename__ = 'factor_exposures'
    
    id = Column(Integer, primary_key=True)
    run_id = Column(String(50), ForeignKey('runs.run_id'), nullable=False, index=True)
    
    # Factor details
    factor_name = Column(String(50), nullable=False)  # market, size, value, momentum, quality, low_vol
    factor_type = Column(String(20))  # style, risk, sector
    
    # Exposure metrics
    exposure = Column(Float, nullable=False)  # Factor loading
    contribution_to_return = Column(Float)  # How much this factor contributed
    contribution_to_risk = Column(Float)  # How much this factor contributed to risk
    
    # Additional metrics as JSON
    metrics_json = Column(Text)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    
    __table_args__ = (
        Index('idx_factor_run_name', 'run_id', 'factor_name'),
    )
    
    def get_metrics(self) -> Dict:
        """Get additional metrics."""
        return json.loads(self.metrics_json) if self.metrics_json else {}
    
    def set_metrics(self, metrics: Dict):
        """Set additional metrics."""
        self.metrics_json = json.dumps(metrics, default=str)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'run_id': self.run_id,
            'factor_name': self.factor_name,
            'factor_type': self.factor_type,
            'exposure': self.exposure,
            'contribution_to_return': self.contribution_to_return,
            'contribution_to_risk': self.contribution_to_risk,
            'metrics': self.get_metrics(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class PerformanceAttribution(Base):
    """Stores performance attribution analysis."""
    __tablename__ = 'performance_attributions'
    
    id = Column(Integer, primary_key=True)
    run_id = Column(String(50), ForeignKey('runs.run_id'), nullable=False, index=True)
    
    # Attribution period
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Total portfolio return
    total_return = Column(Float, nullable=False)
    
    # Attribution components
    factor_attribution = Column(Float)  # Return from factor exposure
    sector_attribution = Column(Float)  # Return from sector allocation
    stock_selection_attribution = Column(Float)  # Return from picking winners
    timing_attribution = Column(Float)  # Return from rebalancing timing
    interaction_attribution = Column(Float)  # Interaction effects
    
    # Detailed breakdown as JSON
    breakdown_json = Column(Text)  # Per-factor, per-sector breakdown
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    
    __table_args__ = (
        Index('idx_attribution_run_dates', 'run_id', 'start_date', 'end_date'),
    )
    
    def get_breakdown(self) -> Dict:
        """Get detailed breakdown."""
        return json.loads(self.breakdown_json) if self.breakdown_json else {}
    
    def set_breakdown(self, breakdown: Dict):
        """Set detailed breakdown."""
        self.breakdown_json = json.dumps(breakdown, default=str)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'run_id': self.run_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'total_return': self.total_return,
            'factor_attribution': self.factor_attribution,
            'sector_attribution': self.sector_attribution,
            'stock_selection_attribution': self.stock_selection_attribution,
            'timing_attribution': self.timing_attribution,
            'interaction_attribution': self.interaction_attribution,
            'breakdown': self.get_breakdown(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
