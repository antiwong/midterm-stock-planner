"""
Recommendation Performance Tracker
==================================
Tracks AI recommendation performance over time by comparing predictions to actual results.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import yfinance as yf
import warnings

from .models import get_db, Run
from .analysis_models import Recommendation
from .analysis_service import AnalysisService


class RecommendationTracker:
    """Tracks recommendation performance over time."""
    
    def __init__(self, db_path: str = "data/analysis.db"):
        """Initialize the recommendation tracker."""
        self.db = get_db(db_path)
        self.analysis_service = AnalysisService(db_path)
    
    def update_recommendation_performance(
        self,
        recommendation_id: int,
        end_date: Optional[datetime] = None
    ) -> Optional[Recommendation]:
        """
        Update a recommendation's performance metrics.
        
        Args:
            recommendation_id: ID of the recommendation to update
            end_date: Date to calculate performance to (default: today)
            
        Returns:
            Updated Recommendation object or None if not found
        """
        session = self.db.get_session()
        try:
            rec = session.query(Recommendation).filter_by(id=recommendation_id).first()
            if not rec:
                return None
            
            # Store values before closing session (if needed for calculation)
            ticker = rec.ticker
            rec_date = rec.recommendation_date
            current_price = rec.current_price
            action = rec.action
            target_price = rec.target_price
            stop_loss = rec.stop_loss
            
            if not end_date:
                end_date = datetime.now()
            
            # Calculate actual return (this may use yfinance, so do it outside session if needed)
            actual_return = self._calculate_actual_return(
                ticker,
                rec_date,
                end_date,
                current_price
            )
            
            # Skip if calculation failed
            if actual_return is None:
                return rec
            
            # Check if hit target or stop loss
            hit_target = False
            hit_stop_loss = False
            
            if target_price and current_price:
                if action in ['BUY', 'HOLD']:
                    target_return = (target_price - current_price) / current_price
                    hit_target = actual_return >= target_return
                else:
                    target_return = (target_price - current_price) / current_price
                    hit_target = actual_return <= target_return
            
            if stop_loss and current_price:
                if action in ['BUY', 'HOLD']:
                    stop_return = (stop_loss - current_price) / current_price
                    hit_stop_loss = actual_return <= stop_return
                else:
                    stop_return = (stop_loss - current_price) / current_price
                    hit_stop_loss = actual_return >= stop_return
            
            # Update recommendation
            rec.actual_return = actual_return
            rec.hit_target = hit_target
            rec.hit_stop_loss = hit_stop_loss
            rec.tracking_updated_at = end_date
            
            session.commit()
            
            # Return a fresh copy to avoid session binding issues
            session.refresh(rec)
            return rec
            
        except Exception as e:
            session.rollback()
            warnings.warn(f"Error updating recommendation {recommendation_id}: {e}")
            return None
        finally:
            session.close()
    
    def update_all_recommendations(
        self,
        run_id: Optional[str] = None,
        days_old: int = 1
    ) -> Dict[str, Any]:
        """
        Update performance for all recommendations.
        
        Args:
            run_id: Optional run ID to filter by
            days_old: Only update recommendations older than this many days
            
        Returns:
            Summary dictionary with update statistics
        """
        session = self.db.get_session()
        try:
            query = session.query(Recommendation)
            
            if run_id:
                query = query.filter_by(run_id=run_id)
            
            # Only update recommendations older than days_old
            cutoff_date = datetime.now() - timedelta(days=days_old)
            query = query.filter(Recommendation.recommendation_date <= cutoff_date)
            
            # Get recommendation IDs only (to avoid session binding issues)
            recommendation_ids = [rec.id for rec in query.all()]
            
            updated = 0
            errors = 0
            total_return = 0.0
            hit_targets = 0
            hit_stop_losses = 0
            
            for rec_id in recommendation_ids:
                try:
                    updated_rec = self.update_recommendation_performance(rec_id)
                    if updated_rec and updated_rec.actual_return is not None:
                        updated += 1
                        total_return += updated_rec.actual_return
                        if updated_rec.hit_target:
                            hit_targets += 1
                        if updated_rec.hit_stop_loss:
                            hit_stop_losses += 1
                except Exception as e:
                    errors += 1
                    warnings.warn(f"Error updating recommendation {rec_id}: {e}")
            
            avg_return = total_return / updated if updated > 0 else 0.0
            
            return {
                'total': len(recommendation_ids),
                'updated': updated,
                'errors': errors,
                'avg_return': avg_return,
                'hit_target_rate': hit_targets / updated if updated > 0 else 0.0,
                'hit_stop_loss_rate': hit_stop_losses / updated if updated > 0 else 0.0,
            }
            
        finally:
            session.close()
    
    def get_recommendation_performance_summary(
        self,
        run_id: Optional[str] = None,
        action: Optional[str] = None,
        min_days_old: int = 7
    ) -> Dict[str, Any]:
        """
        Get performance summary for recommendations.
        
        Args:
            run_id: Optional run ID to filter by
            action: Optional action type (BUY, SELL, HOLD, AVOID)
            min_days_old: Minimum age in days for recommendations to include
            
        Returns:
            Summary dictionary with performance metrics
        """
        session = self.db.get_session()
        try:
            query = session.query(Recommendation)
            
            if run_id:
                query = query.filter_by(run_id=run_id)
            
            if action:
                query = query.filter_by(action=action)
            
            # Only include recommendations old enough to have meaningful performance
            cutoff_date = datetime.now() - timedelta(days=min_days_old)
            query = query.filter(Recommendation.recommendation_date <= cutoff_date)
            
            recommendations = query.all()
            
            if not recommendations:
                return {
                    'total': 0,
                    'with_tracking': 0,
                    'avg_return': 0.0,
                    'win_rate': 0.0,
                    'hit_target_rate': 0.0,
                    'hit_stop_loss_rate': 0.0,
                }
            
            tracked = [r for r in recommendations if r.actual_return is not None]
            
            if not tracked:
                return {
                    'total': len(recommendations),
                    'with_tracking': 0,
                    'avg_return': 0.0,
                    'win_rate': 0.0,
                    'hit_target_rate': 0.0,
                    'hit_stop_loss_rate': 0.0,
                }
            
            returns = [r.actual_return for r in tracked]
            avg_return = np.mean(returns)
            win_rate = sum(1 for r in returns if r > 0) / len(returns) if returns else 0.0
            
            hit_targets = sum(1 for r in tracked if r.hit_target)
            hit_stop_losses = sum(1 for r in tracked if r.hit_stop_loss)
            
            return {
                'total': len(recommendations),
                'with_tracking': len(tracked),
                'avg_return': avg_return,
                'median_return': np.median(returns) if returns else 0.0,
                'win_rate': win_rate,
                'hit_target_rate': hit_targets / len(tracked) if tracked else 0.0,
                'hit_stop_loss_rate': hit_stop_losses / len(tracked) if tracked else 0.0,
                'best_return': max(returns) if returns else 0.0,
                'worst_return': min(returns) if returns else 0.0,
            }
            
        finally:
            session.close()
    
    def get_recommendations_by_performance(
        self,
        run_id: Optional[str] = None,
        action: Optional[str] = None,
        min_return: Optional[float] = None,
        max_return: Optional[float] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recommendations filtered by performance.
        
        Args:
            run_id: Optional run ID to filter by
            action: Optional action type
            min_return: Minimum return threshold
            max_return: Maximum return threshold
            limit: Maximum number of results
            
        Returns:
            List of recommendation dictionaries
        """
        session = self.db.get_session()
        try:
            query = session.query(Recommendation)
            
            if run_id:
                query = query.filter_by(run_id=run_id)
            
            if action:
                query = query.filter_by(action=action)
            
            if min_return is not None:
                query = query.filter(Recommendation.actual_return >= min_return)
            
            if max_return is not None:
                query = query.filter(Recommendation.actual_return <= max_return)
            
            query = query.filter(Recommendation.actual_return.isnot(None))
            query = query.order_by(Recommendation.actual_return.desc())
            query = query.limit(limit)
            
            recommendations = query.all()
            return [r.to_dict() for r in recommendations]
            
        finally:
            session.close()
    
    def _calculate_actual_return(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        start_price: Optional[float] = None
    ) -> Optional[float]:
        """
        Calculate actual return for a ticker over a date range.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date
            end_date: End date
            start_price: Optional starting price (if None, fetched from data)
            
        Returns:
            Actual return as decimal (e.g., 0.15 for 15%) or None if error
        """
        try:
            # Fetch price data
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty:
                return None
            
            # Get start and end prices
            if start_price:
                start_p = start_price
            else:
                start_p = hist.iloc[0]['Close']
            
            end_p = hist.iloc[-1]['Close']
            
            # Calculate return
            if start_p and start_p > 0:
                return (end_p - start_p) / start_p
            else:
                return None
                
        except Exception as e:
            warnings.warn(f"Error calculating return for {ticker}: {e}")
            return None
