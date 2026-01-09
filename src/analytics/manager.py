"""
Run Manager
===========
High-level API for managing analysis runs.
"""

import uuid
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from contextlib import contextmanager
import json

from .models import get_db, Run, StockScore, Trade, PortfolioSnapshot, DatabaseManager


class RunContext:
    """Context manager for tracking a single analysis run."""
    
    def __init__(self, manager: "RunManager", run_id: str):
        self.manager = manager
        self.run_id = run_id
        self.start_time = time.time()
        self._scores = []
        self._trades = []
        self._snapshots = []
    
    def __enter__(self) -> "RunContext":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.complete(status='failed', description=str(exc_val))
        return False
    
    def add_score(
        self,
        ticker: str,
        score: float,
        rank: Optional[int] = None,
        percentile: Optional[float] = None,
        tech_score: Optional[float] = None,
        fund_score: Optional[float] = None,
        sent_score: Optional[float] = None,
        predicted_return: Optional[float] = None,
        features: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Add a stock score to the run."""
        self._scores.append({
            'ticker': ticker,
            'score': score,
            'rank': rank,
            'percentile': percentile,
            'tech_score': tech_score,
            'fund_score': fund_score,
            'sent_score': sent_score,
            'predicted_return': predicted_return,
            'features': features or {},
            **kwargs
        })
    
    def add_trade(
        self,
        trade_date: datetime,
        ticker: str,
        action: str,
        quantity: float,
        price: float,
        **kwargs
    ):
        """Add a trade to the run."""
        self._trades.append({
            'trade_date': trade_date,
            'ticker': ticker,
            'action': action,
            'quantity': quantity,
            'price': price,
            **kwargs
        })
    
    def add_portfolio_snapshot(
        self,
        snapshot_date: datetime,
        portfolio_value: float,
        **kwargs
    ):
        """Add a portfolio snapshot to the run."""
        self._snapshots.append({
            'snapshot_date': snapshot_date,
            'portfolio_value': portfolio_value,
            **kwargs
        })
    
    def set_metrics(self, **kwargs):
        """Set run metrics."""
        self.manager._update_run_metrics(self.run_id, kwargs)
    
    def complete(self, status: str = 'completed', description: Optional[str] = None):
        """Mark the run as complete and save all data."""
        duration = time.time() - self.start_time
        
        # Save scores
        if self._scores:
            self.manager._save_scores(self.run_id, self._scores)
        
        # Save trades
        if self._trades:
            self.manager._save_trades(self.run_id, self._trades)
        
        # Save snapshots
        if self._snapshots:
            self.manager._save_snapshots(self.run_id, self._snapshots)
        
        # Update run status
        self.manager._complete_run(
            self.run_id,
            status=status,
            duration=duration,
            description=description
        )


class RunManager:
    """Manages the lifecycle and data storage for analysis runs."""
    
    def __init__(self, db_path: str = "data/analysis.db"):
        self.db = get_db(db_path)
    
    def _generate_run_id(self) -> str:
        """Generate a unique run ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_suffix = uuid.uuid4().hex[:8]
        return f"{timestamp}_{unique_suffix}"
    
    def start_run(
        self,
        run_type: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        universe: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        watchlist: Optional[str] = None,
        watchlist_display_name: Optional[str] = None,
    ) -> RunContext:
        """Start a new analysis run.
        
        Args:
            run_type: Type of run (backtest, score, optimization)
            name: Optional run name
            description: Optional description
            config: Configuration dictionary
            universe: List of ticker symbols
            tags: Optional list of tags
            watchlist: Watchlist identifier (e.g., 'tech_giants')
            watchlist_display_name: Human-readable watchlist name
        """
        run_id = self._generate_run_id()
        
        session = self.db.get_session()
        try:
            run = Run(
                run_id=run_id,
                name=name,
                run_type=run_type,
                description=description,
                status='in_progress',
                created_at=datetime.now(),
                started_at=datetime.now(),
                watchlist=watchlist,
                watchlist_display_name=watchlist_display_name,
            )
            
            if tags:
                run.set_tags(tags)
            if config:
                run.set_config(config)
            if universe:
                run.set_universe(universe)
            
            session.add(run)
            session.commit()
            
            return RunContext(self, run_id)
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def _update_run_metrics(self, run_id: str, metrics: Dict[str, Any]):
        """Update run metrics."""
        session = self.db.get_session()
        try:
            run = session.query(Run).filter_by(run_id=run_id).first()
            if run:
                # Update direct metrics
                for key, value in metrics.items():
                    if hasattr(run, key):
                        setattr(run, key, value)
                
                # Store extra metrics in JSON
                existing = run.get_metrics()
                existing.update(metrics)
                run.set_metrics(existing)
                
                session.commit()
        finally:
            session.close()
    
    def _save_scores(self, run_id: str, scores: List[Dict]):
        """Save stock scores for a run."""
        session = self.db.get_session()
        try:
            for score_data in scores:
                score = StockScore(
                    run_id=run_id,
                    ticker=score_data['ticker'],
                    score=score_data['score'],
                    rank=score_data.get('rank'),
                    percentile=score_data.get('percentile'),
                    tech_score=score_data.get('tech_score'),
                    fund_score=score_data.get('fund_score'),
                    sent_score=score_data.get('sent_score'),
                    predicted_return=score_data.get('predicted_return'),
                    rsi=score_data.get('rsi'),
                    return_21d=score_data.get('return_21d'),
                    return_63d=score_data.get('return_63d'),
                    volatility=score_data.get('volatility'),
                    sector=score_data.get('sector'),
                )
                
                if 'features' in score_data:
                    score.set_features(score_data['features'])
                
                session.add(score)
            
            session.commit()
        finally:
            session.close()
    
    def _save_trades(self, run_id: str, trades: List[Dict]):
        """Save trades for a run."""
        session = self.db.get_session()
        try:
            for trade_data in trades:
                trade = Trade(
                    run_id=run_id,
                    trade_date=trade_data['trade_date'],
                    ticker=trade_data['ticker'],
                    action=trade_data['action'],
                    quantity=trade_data['quantity'],
                    price=trade_data['price'],
                    value=trade_data.get('value'),
                    commission=trade_data.get('commission', 0),
                    signal_score=trade_data.get('signal_score'),
                    reason=trade_data.get('reason'),
                )
                session.add(trade)
            
            session.commit()
        finally:
            session.close()
    
    def _save_snapshots(self, run_id: str, snapshots: List[Dict]):
        """Save portfolio snapshots for a run."""
        session = self.db.get_session()
        try:
            for snap_data in snapshots:
                snapshot = PortfolioSnapshot(
                    run_id=run_id,
                    snapshot_date=snap_data['snapshot_date'],
                    portfolio_value=snap_data['portfolio_value'],
                    cash=snap_data.get('cash'),
                    equity=snap_data.get('equity'),
                    daily_return=snap_data.get('daily_return'),
                    cumulative_return=snap_data.get('cumulative_return'),
                    drawdown=snap_data.get('drawdown'),
                )
                
                if 'holdings' in snap_data:
                    snapshot.holdings_json = json.dumps(snap_data['holdings'])
                
                session.add(snapshot)
            
            session.commit()
        finally:
            session.close()
    
    def _complete_run(
        self,
        run_id: str,
        status: str = 'completed',
        duration: Optional[float] = None,
        description: Optional[str] = None
    ):
        """Mark a run as complete."""
        session = self.db.get_session()
        try:
            run = session.query(Run).filter_by(run_id=run_id).first()
            if run:
                run.status = status
                run.completed_at = datetime.now()
                if duration:
                    run.duration_seconds = duration
                if description:
                    run.description = description
                session.commit()
        finally:
            session.close()
    
    def get_run(self, run_id: str) -> Optional[Run]:
        """Get a run by ID."""
        session = self.db.get_session()
        try:
            return session.query(Run).filter_by(run_id=run_id).first()
        finally:
            session.close()
    
    def list_runs(
        self,
        run_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Run]:
        """List runs with optional filters."""
        session = self.db.get_session()
        try:
            query = session.query(Run)
            if run_type:
                query = query.filter_by(run_type=run_type)
            if status:
                query = query.filter_by(status=status)
            return query.order_by(Run.created_at.desc()).limit(limit).all()
        finally:
            session.close()
    
    def get_run_scores(self, run_id: str) -> List[Dict]:
        """Get scores for a run."""
        session = self.db.get_session()
        try:
            scores = session.query(StockScore).filter_by(run_id=run_id).order_by(StockScore.rank).all()
            return [s.to_dict() for s in scores]
        finally:
            session.close()
    
    def delete_run(self, run_id: str) -> bool:
        """Delete a run and all associated data."""
        session = self.db.get_session()
        try:
            run = session.query(Run).filter_by(run_id=run_id).first()
            if run:
                session.delete(run)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        session = self.db.get_session()
        try:
            total_runs = session.query(Run).count()
            completed_runs = session.query(Run).filter_by(status='completed').count()
            
            # Count by type
            from sqlalchemy import func
            by_type = dict(session.query(Run.run_type, func.count(Run.id)).group_by(Run.run_type).all())
            
            return {
                'total_runs': total_runs,
                'completed_runs': completed_runs,
                'by_type': by_type,
            }
        finally:
            session.close()


# Convenience functions
def RunManager_instance(db_path: str = "data/analysis.db") -> RunManager:
    """Get a RunManager instance."""
    return RunManager(db_path)
