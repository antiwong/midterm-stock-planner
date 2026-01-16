"""
Real-Time Monitoring
===================
Daily portfolio updates, alert system, and performance tracking.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum

# Import alert system
try:
    from .alert_system import AlertService
    ALERT_SYSTEM_AVAILABLE = True
except ImportError:
    ALERT_SYSTEM_AVAILABLE = False


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class RealTimeMonitor:
    """Monitor portfolio in real-time and generate alerts."""
    
    def __init__(
        self,
        price_change_threshold: float = 0.05,
        volume_spike_threshold: float = 2.0,
        drawdown_threshold: float = -0.10,
        alert_service: Optional[Any] = None,
        run_id: Optional[str] = None
    ):
        """
        Initialize real-time monitor.
        
        Args:
            price_change_threshold: Threshold for price change alerts (default 5%)
            volume_spike_threshold: Threshold for volume spike (default 2x)
            drawdown_threshold: Threshold for drawdown alerts (default -10%)
            alert_service: Optional AlertService instance for sending notifications
            run_id: Optional run ID for alert tracking
        """
        self.price_change_threshold = price_change_threshold
        self.volume_spike_threshold = volume_spike_threshold
        self.drawdown_threshold = drawdown_threshold
        self.alerts = []
        self.alert_service = alert_service
        self.run_id = run_id
    
    def check_portfolio_alerts(
        self,
        portfolio_returns: pd.Series,
        portfolio_weights: pd.DataFrame,
        stock_returns: Optional[pd.DataFrame] = None,
        stock_volumes: Optional[pd.DataFrame] = None,
        benchmark_returns: Optional[pd.Series] = None
    ) -> List[Dict[str, Any]]:
        """
        Check for various alert conditions.
        
        Args:
            portfolio_returns: Portfolio returns time series
            portfolio_weights: Current portfolio weights
            stock_returns: Optional stock returns for individual alerts
            stock_volumes: Optional stock volumes for volume alerts
            benchmark_returns: Optional benchmark for comparison
            
        Returns:
            List of alert dictionaries
        """
        alerts = []
        
        # 1. Drawdown alert
        if len(portfolio_returns) > 0:
            current_drawdown = self._calculate_current_drawdown(portfolio_returns)
            if current_drawdown <= self.drawdown_threshold:
                alerts.append({
                    'type': 'drawdown',
                    'level': AlertLevel.CRITICAL.value,
                    'message': f'Portfolio drawdown: {current_drawdown:.2%}',
                    'value': float(current_drawdown),
                    'threshold': float(self.drawdown_threshold),
                    'timestamp': datetime.now().isoformat()
                })
        
        # 2. Large position changes
        if len(portfolio_weights) >= 2:
            weight_changes = portfolio_weights.iloc[-1] - portfolio_weights.iloc[-2]
            large_changes = weight_changes[abs(weight_changes) > 0.05]  # 5% change
            
            for ticker, change in large_changes.items():
                alerts.append({
                    'type': 'position_change',
                    'level': AlertLevel.WARNING.value,
                    'message': f'{ticker}: Weight changed by {change:.2%}',
                    'ticker': ticker,
                    'change': float(change),
                    'timestamp': datetime.now().isoformat()
                })
        
        # 3. Stock price alerts
        if stock_returns is not None and len(stock_returns) > 0:
            latest_returns = stock_returns.iloc[-1]
            large_moves = latest_returns[abs(latest_returns) > self.price_change_threshold]
            
            for ticker, return_val in large_moves.items():
                if ticker in portfolio_weights.columns:
                    weight = portfolio_weights.iloc[-1][ticker]
                    if abs(weight) > 0.01:  # Only alert on significant positions
                        alerts.append({
                            'type': 'price_movement',
                            'level': AlertLevel.WARNING.value if abs(return_val) < 0.10 else AlertLevel.CRITICAL.value,
                            'message': f'{ticker}: {return_val:.2%} move (position: {weight:.2%})',
                            'ticker': ticker,
                            'return': float(return_val),
                            'position_weight': float(weight),
                            'timestamp': datetime.now().isoformat()
                        })
        
        # 4. Volume spike alerts
        if stock_volumes is not None and len(stock_volumes) > 1:
            latest_volume = stock_volumes.iloc[-1]
            avg_volume = stock_volumes.iloc[:-1].mean()
            volume_ratios = latest_volume / avg_volume.replace(0, np.nan)
            spikes = volume_ratios[volume_ratios > self.volume_spike_threshold]
            
            for ticker, ratio in spikes.items():
                if ticker in portfolio_weights.columns:
                    weight = portfolio_weights.iloc[-1][ticker]
                    if abs(weight) > 0.01:
                        alerts.append({
                            'type': 'volume_spike',
                            'level': AlertLevel.INFO.value,
                            'message': f'{ticker}: Volume spike {ratio:.1f}x average',
                            'ticker': ticker,
                            'volume_ratio': float(ratio),
                            'position_weight': float(weight),
                            'timestamp': datetime.now().isoformat()
                        })
        
        # 5. Underperformance vs benchmark
        if benchmark_returns is not None and len(portfolio_returns) > 0:
            recent_periods = 5
            if len(portfolio_returns) >= recent_periods:
                portfolio_recent = portfolio_returns.tail(recent_periods).mean()
                benchmark_recent = benchmark_returns.tail(recent_periods).mean()
                underperformance = portfolio_recent - benchmark_recent
                
                if underperformance < -0.02:  # Underperforming by 2%
                    alerts.append({
                        'type': 'underperformance',
                        'level': AlertLevel.WARNING.value,
                        'message': f'Portfolio underperforming benchmark by {underperformance:.2%} (5-day avg)',
                        'underperformance': float(underperformance),
                        'portfolio_return': float(portfolio_recent),
                        'benchmark_return': float(benchmark_recent),
                        'timestamp': datetime.now().isoformat()
                    })
        
        # 6. Concentration risk
        if len(portfolio_weights) > 0:
            latest_weights = portfolio_weights.iloc[-1].abs()
            top_5_concentration = latest_weights.nlargest(5).sum()
            
            if top_5_concentration > 0.60:  # Top 5 positions > 60%
                alerts.append({
                    'type': 'concentration',
                    'level': AlertLevel.WARNING.value,
                    'message': f'High concentration: Top 5 positions = {top_5_concentration:.2%}',
                    'concentration': float(top_5_concentration),
                    'timestamp': datetime.now().isoformat()
                })
        
        # Store alerts
        self.alerts = alerts
        
        # Send alerts via alert service if available
        if self.alert_service and self.run_id and ALERT_SYSTEM_AVAILABLE:
            for alert in alerts:
                try:
                    self.alert_service.check_and_send_alerts(
                        self.run_id,
                        {
                            'type': alert.get('type', 'custom'),
                            'level': alert.get('level', 'info'),
                            'message': alert.get('message', ''),
                            'value': alert.get('value'),
                            'data': {k: v for k, v in alert.items() if k not in ['type', 'level', 'message', 'value']}
                        }
                    )
                except Exception as e:
                    # Log but don't fail monitoring
                    import logging
                    logging.warning(f"Error sending alert: {e}")
        
        return alerts
    
    def _calculate_current_drawdown(self, returns: pd.Series) -> float:
        """Calculate current drawdown from peak."""
        cumulative = (1 + returns).cumprod()
        peak = cumulative.expanding().max()
        current_drawdown = (cumulative.iloc[-1] - peak.iloc[-1]) / peak.iloc[-1]
        return float(current_drawdown)
    
    def generate_daily_summary(
        self,
        portfolio_returns: pd.Series,
        portfolio_weights: pd.DataFrame,
        benchmark_returns: Optional[pd.Series] = None
    ) -> Dict[str, Any]:
        """
        Generate daily portfolio summary.
        
        Args:
            portfolio_returns: Portfolio returns
            portfolio_weights: Portfolio weights
            benchmark_returns: Optional benchmark
            
        Returns:
            Dictionary with daily summary
        """
        if len(portfolio_returns) == 0:
            return {'error': 'No portfolio data'}
        
        latest_date = portfolio_returns.index[-1]
        latest_return = portfolio_returns.iloc[-1]
        
        # Calculate metrics
        summary = {
            'date': latest_date.isoformat() if isinstance(latest_date, datetime) else str(latest_date),
            'daily_return': float(latest_return),
            'ytd_return': float((1 + portfolio_returns).prod() - 1) if len(portfolio_returns) > 0 else 0.0,
            'volatility_30d': float(portfolio_returns.tail(30).std() * np.sqrt(252)) if len(portfolio_returns) >= 30 else None,
            'sharpe_30d': float(
                portfolio_returns.tail(30).mean() / portfolio_returns.tail(30).std() * np.sqrt(252)
            ) if len(portfolio_returns) >= 30 and portfolio_returns.tail(30).std() > 0 else None,
            'current_drawdown': float(self._calculate_current_drawdown(portfolio_returns)),
        }
        
        # Portfolio composition
        if len(portfolio_weights) > 0:
            latest_weights = portfolio_weights.iloc[-1]
            top_positions = latest_weights.abs().nlargest(10)
            
            summary['top_positions'] = {
                ticker: float(weight)
                for ticker, weight in top_positions.items()
            }
            summary['position_count'] = int((latest_weights.abs() > 0.001).sum())
            summary['concentration_top_5'] = float(top_positions.head(5).sum())
        
        # Benchmark comparison
        if benchmark_returns is not None and len(benchmark_returns) > 0:
            benchmark_latest = benchmark_returns.iloc[-1]
            summary['benchmark_return'] = float(benchmark_latest)
            summary['excess_return'] = float(latest_return - benchmark_latest)
            summary['ytd_excess'] = float(
                (1 + portfolio_returns).prod() - (1 + benchmark_returns).prod()
            ) if len(portfolio_returns) > 0 and len(benchmark_returns) > 0 else 0.0
        
        return summary
    
    def track_performance_metrics(
        self,
        portfolio_returns: pd.Series,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Track key performance metrics over a period.
        
        Args:
            portfolio_returns: Portfolio returns
            period_days: Number of days to track
            
        Returns:
            Dictionary with performance metrics
        """
        if len(portfolio_returns) < period_days:
            return {'error': f'Insufficient data (need {period_days} days)'}
        
        recent_returns = portfolio_returns.tail(period_days)
        
        metrics = {
            'period_days': period_days,
            'total_return': float(recent_returns.sum()),
            'annualized_return': float(recent_returns.mean() * 252),
            'volatility': float(recent_returns.std() * np.sqrt(252)),
            'sharpe_ratio': float(
                recent_returns.mean() / recent_returns.std() * np.sqrt(252)
            ) if recent_returns.std() > 0 else None,
            'max_drawdown': float(self._calculate_max_drawdown(recent_returns)),
            'win_rate': float((recent_returns > 0).mean()),
            'avg_win': float(recent_returns[recent_returns > 0].mean()) if (recent_returns > 0).any() else 0.0,
            'avg_loss': float(recent_returns[recent_returns < 0].mean()) if (recent_returns < 0).any() else 0.0,
        }
        
        return metrics
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown."""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return float(drawdown.min())
