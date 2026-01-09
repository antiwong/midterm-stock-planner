"""
Run Manager for Mid-term Stock Planner.

Manages the complete lifecycle of analysis runs including:
- Creating and tracking runs
- Saving results to database
- Generating reports
- Comparing runs
"""

import time
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
import logging

from .database import RunDatabase, RunRecord

logger = logging.getLogger(__name__)


@dataclass
class RunContext:
    """Context manager for a single run."""
    run_id: str
    run_type: str
    db: RunDatabase
    start_time: float = field(default_factory=time.time)
    
    # Collected data during run
    config: Optional[Dict] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    scores: List[Dict] = field(default_factory=list)
    trades: List[Dict] = field(default_factory=list)
    portfolio_history: List[Dict] = field(default_factory=list)
    
    # Paths
    output_dir: Optional[Path] = None
    
    def set_metrics(self, **kwargs) -> None:
        """Set metrics for the run."""
        self.metrics.update(kwargs)
    
    def add_score(self, ticker: str, score: float, rank: int, **kwargs) -> None:
        """Add a stock score."""
        self.scores.append({
            'ticker': ticker,
            'score': score,
            'rank': rank,
            **kwargs
        })
    
    def add_trade(self, date: str, ticker: str, action: str, **kwargs) -> None:
        """Add a trade record."""
        self.trades.append({
            'date': date,
            'ticker': ticker,
            'action': action,
            **kwargs
        })
    
    def add_portfolio_snapshot(self, date: str, portfolio_value: float, **kwargs) -> None:
        """Add portfolio history snapshot."""
        self.portfolio_history.append({
            'date': date,
            'portfolio_value': portfolio_value,
            **kwargs
        })
    
    def complete(
        self,
        status: str = "completed",
        report_path: Optional[str] = None,
        model_path: Optional[str] = None,
        chart_path: Optional[str] = None,
    ) -> None:
        """Mark run as complete and save all data."""
        duration = time.time() - self.start_time
        
        # Update run record
        self.db.update_run(
            self.run_id,
            status=status,
            metrics=self.metrics,
            total_return=self.metrics.get('total_return'),
            sharpe_ratio=self.metrics.get('sharpe_ratio'),
            max_drawdown=self.metrics.get('max_drawdown'),
            win_rate=self.metrics.get('win_rate'),
            start_date=self.metrics.get('start_date'),
            end_date=self.metrics.get('end_date'),
            duration_seconds=duration,
            report_path=report_path,
            model_path=model_path,
            chart_path=chart_path,
        )
        
        # Save scores
        if self.scores:
            self.db.add_stock_scores(self.run_id, self.scores)
        
        # Save trades
        if self.trades:
            self.db.add_trades(self.run_id, self.trades)
        
        # Save portfolio history
        if self.portfolio_history:
            self.db.add_portfolio_history(self.run_id, self.portfolio_history)
        
        logger.info(f"Run {self.run_id} completed in {duration:.2f}s")
    
    def fail(self, error: str) -> None:
        """Mark run as failed."""
        duration = time.time() - self.start_time
        
        self.metrics['error'] = error
        
        self.db.update_run(
            self.run_id,
            status="failed",
            metrics=self.metrics,
            duration_seconds=duration,
        )
        
        logger.error(f"Run {self.run_id} failed: {error}")


class RunManager:
    """
    Manages analysis runs with database persistence and reporting.
    
    Usage:
        manager = RunManager()
        
        # Start a new run
        with manager.start_run("backtest", config=my_config, name="Test Run") as ctx:
            # Run your analysis
            results = run_backtest(...)
            
            # Record results
            ctx.set_metrics(
                total_return=results.total_return,
                sharpe_ratio=results.sharpe,
            )
            
            # Add scores
            for ticker, score in results.scores.items():
                ctx.add_score(ticker, score, rank=...)
        
        # List past runs
        runs = manager.list_runs()
        
        # Compare runs
        comparison = manager.compare_runs([run1_id, run2_id])
        
        # Delete a run
        manager.delete_run(run_id)
    """
    
    def __init__(
        self,
        db_path: str | Path = "data/runs.db",
        output_dir: str | Path = "output",
    ):
        """
        Initialize RunManager.
        
        Args:
            db_path: Path to SQLite database
            output_dir: Directory for reports and artifacts
        """
        self.db = RunDatabase(db_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def start_run(
        self,
        run_type: str,
        config: Optional[Dict] = None,
        universe: Optional[List[str]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        watchlist: Optional[str] = None,
        watchlist_display_name: Optional[str] = None,
    ) -> RunContext:
        """
        Start a new run and return a context manager.
        
        Args:
            run_type: Type of run (backtest, score, ab_comparison)
            config: Configuration dictionary
            universe: List of ticker symbols
            name: Optional run name
            description: Optional description
            tags: Optional list of tags
            watchlist: Watchlist identifier (e.g., 'tech_giants')
            watchlist_display_name: Human-readable watchlist name
            
        Returns:
            RunContext for tracking the run
        """
        run_id = self.db.create_run(
            run_type=run_type,
            config=config,
            universe=universe,
            name=name,
            description=description,
            tags=tags,
            watchlist=watchlist,
            watchlist_display_name=watchlist_display_name,
        )
        
        ctx = RunContext(
            run_id=run_id,
            run_type=run_type,
            db=self.db,
            config=config,
            output_dir=self.output_dir / run_id,
        )
        
        # Create output directory for this run
        if ctx.output_dir:
            ctx.output_dir.mkdir(parents=True, exist_ok=True)
        
        return ctx
    
    def get_run(self, run_id: str) -> Optional[RunRecord]:
        """Get a run by ID."""
        return self.db.get_run(run_id)
    
    def list_runs(
        self,
        run_type: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[RunRecord]:
        """List runs with optional filtering."""
        return self.db.list_runs(
            run_type=run_type,
            status=status,
            tags=tags,
            limit=limit,
            offset=offset,
        )
    
    def delete_run(self, run_id: str) -> bool:
        """Delete a run and all associated data."""
        # Also delete any saved artifacts
        run = self.db.get_run(run_id)
        if run:
            run_output_dir = self.output_dir / run_id
            if run_output_dir.exists():
                import shutil
                shutil.rmtree(run_output_dir)
        
        return self.db.delete_run(run_id)
    
    def delete_runs(self, run_ids: List[str]) -> int:
        """Delete multiple runs."""
        for run_id in run_ids:
            run_output_dir = self.output_dir / run_id
            if run_output_dir.exists():
                import shutil
                shutil.rmtree(run_output_dir)
        
        return self.db.delete_runs(run_ids)
    
    def get_run_scores(self, run_id: str, top_n: Optional[int] = None) -> List[Dict]:
        """Get stock scores for a run."""
        return self.db.get_stock_scores(run_id, top_n=top_n)
    
    def get_run_trades(self, run_id: str) -> List[Dict]:
        """Get trades for a run."""
        return self.db.get_trades(run_id)
    
    def get_run_portfolio_history(self, run_id: str) -> List[Dict]:
        """Get portfolio history for a run."""
        return self.db.get_portfolio_history(run_id)
    
    def compare_runs(self, run_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple runs."""
        return self.db.compare_runs(run_ids)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics."""
        return self.db.get_run_stats()
    
    def update_run_name(self, run_id: str, name: str) -> bool:
        """Update a run's name."""
        return self.db.update_run(run_id, name=name)
    
    def update_run_description(self, run_id: str, description: str) -> bool:
        """Update a run's description."""
        return self.db.update_run(run_id, description=description)
    
    def add_run_tags(self, run_id: str, tags: List[str]) -> bool:
        """Add tags to a run."""
        run = self.db.get_run(run_id)
        if not run:
            return False
        
        existing_tags = run.tags.split(",") if run.tags else []
        new_tags = list(set(existing_tags + tags))
        
        return self.db.update_run(run_id, tags=new_tags)
    
    def search_runs(
        self,
        query: str,
        limit: int = 20,
    ) -> List[RunRecord]:
        """Search runs by name or description."""
        # Simple search - could be enhanced with full-text search
        all_runs = self.db.list_runs(limit=1000)
        
        query_lower = query.lower()
        matches = []
        
        for run in all_runs:
            if (
                (run.name and query_lower in run.name.lower()) or
                (run.description and query_lower in run.description.lower()) or
                (run.tags and query_lower in run.tags.lower()) or
                query_lower in run.run_id.lower()
            ):
                matches.append(run)
                if len(matches) >= limit:
                    break
        
        return matches


# Convenience functions
_default_manager: Optional[RunManager] = None


def get_run_manager(
    db_path: str | Path = "data/runs.db",
    output_dir: str | Path = "output",
) -> RunManager:
    """Get or create the default run manager."""
    global _default_manager
    if _default_manager is None:
        _default_manager = RunManager(db_path=db_path, output_dir=output_dir)
    return _default_manager


def start_run(
    run_type: str,
    config: Optional[Dict] = None,
    **kwargs,
) -> RunContext:
    """Start a new run using the default manager."""
    return get_run_manager().start_run(run_type, config=config, **kwargs)
