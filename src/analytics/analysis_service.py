"""
Analysis Service Layer
======================
Service layer for saving and retrieving analysis results from database.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib
import json

from .models import get_db, Run
from .analysis_models import (
    AnalysisResult, AIInsight, Recommendation,
    BenchmarkComparison, FactorExposure, PerformanceAttribution
)


class AnalysisService:
    """Service for managing analysis results in database."""
    
    def __init__(self, db_path: str = "data/analysis.db"):
        self.db = get_db(db_path)
    
    def save_analysis_result(
        self,
        run_id: str,
        analysis_type: str,
        results: Dict[str, Any],
        summary: Optional[Dict[str, Any]] = None,
        status: str = 'completed',
        error_message: Optional[str] = None
    ) -> AnalysisResult:
        """Save analysis results to database."""
        session = self.db.get_session()
        try:
            # Check if result already exists
            existing = session.query(AnalysisResult).filter_by(
                run_id=run_id,
                analysis_type=analysis_type
            ).first()
            
            if existing:
                # Update existing
                existing.set_results(results)
                if summary:
                    existing.set_summary(summary)
                existing.status = status
                existing.error_message = error_message
                existing.updated_at = datetime.now()
                result = existing
            else:
                # Create new
                result = AnalysisResult(
                    run_id=run_id,
                    analysis_type=analysis_type,
                    status=status,
                    error_message=error_message
                )
                result.set_results(results)
                if summary:
                    result.set_summary(summary)
                session.add(result)
            
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_analysis_result(
        self,
        run_id: str,
        analysis_type: str
    ) -> Optional[AnalysisResult]:
        """Get analysis result from database."""
        session = self.db.get_session()
        try:
            result = session.query(AnalysisResult).filter_by(
                run_id=run_id,
                analysis_type=analysis_type
            ).first()
            return result
        finally:
            session.close()
    
    def get_all_analysis_results(
        self,
        run_id: str
    ) -> List[AnalysisResult]:
        """Get all analysis results for a run."""
        session = self.db.get_session()
        try:
            results = session.query(AnalysisResult).filter_by(
                run_id=run_id
            ).order_by(AnalysisResult.created_at.desc()).all()
            return results
        finally:
            session.close()
    
    def save_ai_insight(
        self,
        run_id: str,
        insight_type: str,
        content: str,
        content_json: Optional[Dict] = None,
        context: Optional[Dict] = None,
        model: str = 'gemini',
        model_version: Optional[str] = None,
        prompt_hash: Optional[str] = None,
        status: str = 'completed',
        error_message: Optional[str] = None
    ) -> AIInsight:
        """Save AI insight to database."""
        session = self.db.get_session()
        try:
            # Generate prompt hash if not provided
            if not prompt_hash and context:
                prompt_data = json.dumps(context, sort_keys=True, default=str)
                prompt_hash = hashlib.sha256(prompt_data.encode()).hexdigest()
            
            # Check if similar insight exists (same prompt hash)
            existing = None
            if prompt_hash:
                existing = session.query(AIInsight).filter_by(
                    run_id=run_id,
                    insight_type=insight_type,
                    prompt_hash=prompt_hash
                ).first()
            
            if existing:
                # Update existing
                existing.content = content
                if content_json:
                    existing.set_content_json(content_json)
                if context:
                    existing.set_context(context)
                existing.status = status
                existing.error_message = error_message
                insight = existing
            else:
                # Create new
                insight = AIInsight(
                    run_id=run_id,
                    insight_type=insight_type,
                    content=content,
                    model=model,
                    model_version=model_version,
                    prompt_hash=prompt_hash,
                    status=status,
                    error_message=error_message
                )
                if content_json:
                    insight.set_content_json(content_json)
                if context:
                    insight.set_context(context)
                session.add(insight)
            
            session.commit()
            return insight
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_ai_insight(
        self,
        run_id: str,
        insight_type: str,
        prompt_hash: Optional[str] = None
    ) -> Optional[AIInsight]:
        """Get AI insight from database."""
        session = self.db.get_session()
        try:
            query = session.query(AIInsight).filter_by(
                run_id=run_id,
                insight_type=insight_type
            )
            if prompt_hash:
                query = query.filter_by(prompt_hash=prompt_hash)
            return query.order_by(AIInsight.created_at.desc()).first()
        finally:
            session.close()
    
    def get_all_ai_insights(
        self,
        run_id: str
    ) -> List[AIInsight]:
        """Get all AI insights for a run."""
        session = self.db.get_session()
        try:
            insights = session.query(AIInsight).filter_by(
                run_id=run_id
            ).order_by(AIInsight.created_at.desc()).all()
            return insights
        finally:
            session.close()
    
    def save_recommendations(
        self,
        run_id: str,
        recommendations: List[Dict[str, Any]]
    ) -> List[Recommendation]:
        """Save recommendations to database."""
        session = self.db.get_session()
        try:
            saved = []
            for rec_data in recommendations:
                rec = Recommendation(
                    run_id=run_id,
                    ticker=rec_data.get('ticker'),
                    action=rec_data.get('action', 'BUY'),
                    recommendation_date=rec_data.get('recommendation_date', datetime.now()),
                    reason=rec_data.get('reason'),
                    confidence=rec_data.get('confidence'),
                    target_price=rec_data.get('target_price'),
                    stop_loss=rec_data.get('stop_loss'),
                    time_horizon=rec_data.get('time_horizon', 'medium'),
                    current_price=rec_data.get('current_price'),
                    score=rec_data.get('score'),
                    sector=rec_data.get('sector'),
                    source=rec_data.get('source', 'ai')
                )
                session.add(rec)
                saved.append(rec)
            
            session.commit()
            return saved
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_recommendations(
        self,
        run_id: Optional[str] = None,
        ticker: Optional[str] = None,
        action: Optional[str] = None
    ) -> List[Recommendation]:
        """Get recommendations from database."""
        session = self.db.get_session()
        try:
            query = session.query(Recommendation)
            if run_id:
                query = query.filter_by(run_id=run_id)
            if ticker:
                query = query.filter_by(ticker=ticker)
            if action:
                query = query.filter_by(action=action)
            return query.order_by(Recommendation.recommendation_date.desc()).all()
        finally:
            session.close()
    
    def save_benchmark_comparison(
        self,
        run_id: str,
        benchmark_symbol: str,
        benchmark_name: str,
        start_date: datetime,
        end_date: datetime,
        portfolio_metrics: Dict[str, float],
        benchmark_metrics: Dict[str, float],
        relative_metrics: Dict[str, float],
        additional_metrics: Optional[Dict] = None
    ) -> BenchmarkComparison:
        """Save benchmark comparison to database."""
        session = self.db.get_session()
        try:
            comp = BenchmarkComparison(
                run_id=run_id,
                benchmark_symbol=benchmark_symbol,
                benchmark_name=benchmark_name,
                start_date=start_date,
                end_date=end_date,
                portfolio_return=portfolio_metrics.get('return', 0),
                portfolio_volatility=portfolio_metrics.get('volatility'),
                portfolio_sharpe=portfolio_metrics.get('sharpe'),
                portfolio_max_drawdown=portfolio_metrics.get('max_drawdown'),
                benchmark_return=benchmark_metrics.get('return', 0),
                benchmark_volatility=benchmark_metrics.get('volatility'),
                benchmark_sharpe=benchmark_metrics.get('sharpe'),
                benchmark_max_drawdown=benchmark_metrics.get('max_drawdown'),
                alpha=relative_metrics.get('alpha'),
                beta=relative_metrics.get('beta'),
                tracking_error=relative_metrics.get('tracking_error'),
                information_ratio=relative_metrics.get('information_ratio'),
                up_capture=relative_metrics.get('up_capture'),
                down_capture=relative_metrics.get('down_capture')
            )
            if additional_metrics:
                comp.set_metrics(additional_metrics)
            session.add(comp)
            session.commit()
            return comp
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def save_factor_exposures(
        self,
        run_id: str,
        factor_exposures: List[Dict[str, Any]]
    ) -> List[FactorExposure]:
        """Save factor exposures to database."""
        session = self.db.get_session()
        try:
            # Delete existing exposures for this run
            session.query(FactorExposure).filter_by(run_id=run_id).delete()
            
            saved = []
            for exp_data in factor_exposures:
                exp = FactorExposure(
                    run_id=run_id,
                    factor_name=exp_data.get('factor_name'),
                    factor_type=exp_data.get('factor_type'),
                    exposure=exp_data.get('exposure', 0),
                    contribution_to_return=exp_data.get('contribution_to_return'),
                    contribution_to_risk=exp_data.get('contribution_to_risk')
                )
                if exp_data.get('metrics'):
                    exp.set_metrics(exp_data['metrics'])
                session.add(exp)
                saved.append(exp)
            
            session.commit()
            return saved
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def save_performance_attribution(
        self,
        run_id: str,
        start_date: datetime,
        end_date: datetime,
        total_return: float,
        attributions: Dict[str, float],
        breakdown: Optional[Dict] = None
    ) -> PerformanceAttribution:
        """Save performance attribution to database."""
        session = self.db.get_session()
        try:
            attr = PerformanceAttribution(
                run_id=run_id,
                start_date=start_date,
                end_date=end_date,
                total_return=total_return,
                factor_attribution=attributions.get('factor', 0),
                sector_attribution=attributions.get('sector', 0),
                stock_selection_attribution=attributions.get('stock_selection', 0),
                timing_attribution=attributions.get('timing', 0),
                interaction_attribution=attributions.get('interaction', 0)
            )
            if breakdown:
                attr.set_breakdown(breakdown)
            session.add(attr)
            session.commit()
            return attr
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
