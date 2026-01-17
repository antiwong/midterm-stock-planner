"""
Comprehensive Analysis Runner
=============================
Unified system to run all analysis modules and save results to database.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json

from .analysis_service import AnalysisService
from .performance_attribution import PerformanceAttributionAnalyzer
from .benchmark_comparison import BenchmarkComparator
from .factor_exposure import FactorExposureAnalyzer
from .rebalancing_analysis import RebalancingAnalyzer
from .style_analysis import StyleAnalyzer
from .ai_insights import AIInsightsGenerator
from .data_loader import RunDataLoader, load_run_data_for_analysis
from .data_loader import load_run_data_for_analysis
from .data_completeness import DataCompletenessChecker
from .event_analysis import EventAnalyzer
from .tax_optimization import TaxOptimizer
from .monte_carlo import MonteCarloSimulator
from .turnover_analysis import TurnoverAnalyzer
from .earnings_calendar import EarningsCalendarAnalyzer
from .realtime_monitoring import RealTimeMonitor


class ComprehensiveAnalysisRunner:
    """Run all analysis modules and save to database."""
    
    def __init__(self, db_path: str = "data/analysis.db", strict_validation: bool = True):
        self.service = AnalysisService(db_path)
        self.attribution_analyzer = PerformanceAttributionAnalyzer()
        self.benchmark_comparator = BenchmarkComparator()
        self.factor_analyzer = FactorExposureAnalyzer()
        self.rebalancing_analyzer = RebalancingAnalyzer()
        self.style_analyzer = StyleAnalyzer()
        self.ai_generator = AIInsightsGenerator()
        self.data_checker = DataCompletenessChecker()
        self.event_analyzer = EventAnalyzer()
        self.tax_optimizer = TaxOptimizer()
        self.monte_carlo = MonteCarloSimulator()
        self.turnover_analyzer = TurnoverAnalyzer()
        self.earnings_analyzer = EarningsCalendarAnalyzer()
        self.realtime_monitor = RealTimeMonitor()
        self.strict_validation = strict_validation
    
    def run_all_analysis(
        self,
        run_id: str,
        portfolio_data: Dict[str, Any],
        stock_data: Optional[pd.DataFrame] = None,
        save_ai_insights: bool = True
    ) -> Dict[str, Any]:
        """
        Run all analysis modules for a run.
        
        Args:
            run_id: Analysis run ID
            portfolio_data: Dictionary with portfolio information:
                - returns: pd.Series of portfolio returns
                - weights: pd.DataFrame of portfolio weights over time
                - holdings: List of tickers
                - start_date: datetime
                - end_date: datetime
            stock_data: DataFrame with stock returns and features
            save_ai_insights: Whether to generate and save AI insights
            
        Returns:
            Dictionary with all analysis results
        """
        results = {
            'run_id': run_id,
            'timestamp': datetime.now().isoformat(),
            'analyses': {},
            'data_completeness': None,
            'warnings': [],
            'errors': []
        }
        
        # Check data completeness BEFORE running analyses
        print(f"[{run_id}] Checking data completeness...")
        # Try to load benchmark data if available
        benchmark_data = None
        try:
            from .data_loader import RunDataLoader
            loader = RunDataLoader(Path(run_id).parent if Path(run_id).is_file() else Path("output") / run_id)
            # Benchmark data is optional - benchmark comparison can fetch from yfinance
            # So we pass None to allow the check to proceed
        except:
            pass
        
        completeness = self.data_checker.check_data_completeness(
            portfolio_data,
            stock_data if stock_data is not None else {},
            benchmark_data=benchmark_data  # Optional - benchmark comparison can fetch from API
        )
        
        results['data_completeness'] = completeness
        
        # Print completeness report
        report = self.data_checker.generate_report(completeness)
        print(report)
        
        # Collect warnings and errors
        results['warnings'].extend(completeness.get('warnings', []))
        results['errors'].extend(completeness.get('errors', []))
        
        # If strict validation and critical errors, stop or warn
        if self.strict_validation and completeness.get('errors'):
            print("\n⚠️  CRITICAL: Missing required data for some analyses!")
            print("   Analysis will continue but some results may be incomplete.")
            print("   See data completeness report above for details.\n")
        
        # Run independent analyses in parallel
        parallelized_names = set()
        try:
            from src.app.dashboard.utils.parallel import parallel_calculation
            
            # Define independent analysis functions
            independent_analyses = []
            
            # 1. Performance Attribution (depends on stock_data)
            attribution_status = completeness['analysis_status'].get('attribution', {})
            if attribution_status.get('can_run', False):
                independent_analyses.append(('attribution', lambda: self._run_attribution(
                    run_id, portfolio_data, stock_data
                )))
            
            # 2. Benchmark Comparison (independent)
            independent_analyses.append(('benchmark', lambda: self._run_benchmark_comparison(
                run_id, portfolio_data
            )))
            
            # 3. Factor Exposure (depends on stock_data)
            independent_analyses.append(('factor_exposure', lambda: self._run_factor_exposure(
                run_id, portfolio_data, stock_data
            )))
            
            # 4. Rebalancing Analysis (independent)
            independent_analyses.append(('rebalancing', lambda: self._run_rebalancing_analysis(
                run_id, portfolio_data
            )))
            
            # 5. Style Analysis (depends on stock_data)
            style_status = completeness['analysis_status'].get('style', {})
            if style_status.get('can_run', False):
                independent_analyses.append(('style', lambda: self._run_style_analysis(
                    run_id, portfolio_data, stock_data
                )))
            
            # Run independent analyses in parallel
            if len(independent_analyses) > 1:
                print(f"[{run_id}] Running {len(independent_analyses)} analyses in parallel...")
                analysis_functions = [func for _, func in independent_analyses]
                analysis_results = parallel_calculation(
                    analysis_functions,
                    max_workers=min(4, len(independent_analyses))
                )
                
                # Map results back to analysis names
                for (name, _), result in zip(independent_analyses, analysis_results):
                    parallelized_names.add(name)
                    if result:
                        results['analyses'][name] = result
                    else:
                        results['analyses'][name] = {'error': 'Analysis failed'}
        except ImportError:
            print("   ⚠️  Parallel processing not available, using sequential execution")
        except Exception as e:
            print(f"   ⚠️  Parallel processing failed: {e}, using sequential execution")
        
        # Run remaining analyses sequentially (those that couldn't be parallelized)
        # 1. Performance Attribution (if not already run)
        attribution_status = completeness['analysis_status'].get('attribution', {})
        if attribution_status.get('can_run', False):
            try:
                print(f"[{run_id}] Running performance attribution...")
                attribution_results = self._run_attribution(
                    run_id, portfolio_data, stock_data
                )
                results['analyses']['attribution'] = attribution_results
            except Exception as e:
                print(f"❌ Error in attribution: {e}")
                results['analyses']['attribution'] = {'error': str(e)}
                results['errors'].append({'analysis': 'attribution', 'error': str(e)})
        else:
            print(f"⚠️  Skipping attribution: {attribution_status.get('message', 'Missing required data')}")
            results['analyses']['attribution'] = {
                'error': attribution_status.get('message', 'Missing required data'),
                'skipped': True,
                'missing_data': attribution_status.get('missing', [])
            }
        
        # 2. Benchmark Comparison
        # Benchmark comparison can always run (fetches data from API if needed)
        benchmark_status = completeness['analysis_status'].get('benchmark_comparison', {})
        # Always try to run benchmark comparison (it can fetch from yfinance)
        try:
            print(f"[{run_id}] Running benchmark comparison...")
            benchmark_results = self._run_benchmark_comparison(
                run_id, portfolio_data
            )
            results['analyses']['benchmark'] = benchmark_results
        except Exception as e:
            print(f"❌ Error in benchmark comparison: {e}")
            results['analyses']['benchmark'] = {'error': str(e)}
            results['errors'].append({'analysis': 'benchmark_comparison', 'error': str(e)})
        
        # 3. Factor Exposure
        try:
            print(f"[{run_id}] Running factor exposure analysis...")
            factor_results = self._run_factor_exposure(
                run_id, portfolio_data, stock_data
            )
            results['analyses']['factor_exposure'] = factor_results
        except Exception as e:
            print(f"Error in factor exposure: {e}")
            results['analyses']['factor_exposure'] = {'error': str(e)}
        
        # 4. Rebalancing Analysis
        try:
            print(f"[{run_id}] Running rebalancing analysis...")
            rebalancing_results = self._run_rebalancing_analysis(
                run_id, portfolio_data
            )
            results['analyses']['rebalancing'] = rebalancing_results
        except Exception as e:
            print(f"Error in rebalancing analysis: {e}")
            results['analyses']['rebalancing'] = {'error': str(e)}
        
        # 5. Style Analysis
        style_status = completeness['analysis_status'].get('style', {})
        if style_status.get('can_run', False):
            try:
                print(f"[{run_id}] Running style analysis...")
                style_results = self._run_style_analysis(
                    run_id, portfolio_data, stock_data
                )
                results['analyses']['style'] = style_results
            except Exception as e:
                print(f"❌ Error in style analysis: {e}")
                results['analyses']['style'] = {'error': str(e)}
                results['errors'].append({'analysis': 'style', 'error': str(e)})
        else:
            print(f"⚠️  Skipping style analysis: {style_status.get('message', 'Missing required data')}")
            results['analyses']['style'] = {
                'error': style_status.get('message', 'Missing required data'),
                'skipped': True,
                'missing_data': style_status.get('missing', [])
            }
        
        # 6. AI Insights (if requested)
        if save_ai_insights:
            try:
                print(f"[{run_id}] Checking AI insights...")
                ai_results = self._run_ai_insights(
                    run_id, portfolio_data, stock_data
                )
                results['analyses']['ai_insights'] = ai_results
            except Exception as e:
                print(f"Error in AI insights: {e}")
                results['analyses']['ai_insights'] = {'error': str(e)}
        
        # 7. Event-Driven Analysis
        try:
            print(f"[{run_id}] Running event-driven analysis...")
            event_results = self._run_event_analysis(
                run_id, portfolio_data, stock_data
            )
            results['analyses']['event_analysis'] = event_results
        except Exception as e:
            print(f"Error in event analysis: {e}")
            results['analyses']['event_analysis'] = {'error': str(e)}
        
        # 8. Tax Optimization
        try:
            print(f"[{run_id}] Running tax optimization analysis...")
            tax_results = self._run_tax_optimization(
                run_id, portfolio_data, stock_data
            )
            results['analyses']['tax_optimization'] = tax_results
        except Exception as e:
            print(f"Error in tax optimization: {e}")
            results['analyses']['tax_optimization'] = {'error': str(e)}
        
        # 9. Monte Carlo Simulation
        try:
            print(f"[{run_id}] Running Monte Carlo simulation...")
            mc_results = self._run_monte_carlo(
                run_id, portfolio_data
            )
            results['analyses']['monte_carlo'] = mc_results
        except Exception as e:
            print(f"Error in Monte Carlo: {e}")
            results['analyses']['monte_carlo'] = {'error': str(e)}
        
        # 10. Turnover & Churn Analysis
        try:
            print(f"[{run_id}] Running turnover analysis...")
            turnover_results = self._run_turnover_analysis(
                run_id, portfolio_data
            )
            results['analyses']['turnover'] = turnover_results
        except Exception as e:
            print(f"Error in turnover analysis: {e}")
            results['analyses']['turnover'] = {'error': str(e)}
        
        # 11. Earnings Calendar Analysis
        try:
            print(f"[{run_id}] Running earnings calendar analysis...")
            earnings_results = self._run_earnings_analysis(
                run_id, portfolio_data, stock_data
            )
            results['analyses']['earnings'] = earnings_results
        except Exception as e:
            print(f"Error in earnings analysis: {e}")
            results['analyses']['earnings'] = {'error': str(e)}
        
        # 12. Real-Time Monitoring
        try:
            print(f"[{run_id}] Running real-time monitoring...")
            monitoring_results = self._run_realtime_monitoring(
                run_id, portfolio_data, stock_data
            )
            results['analyses']['realtime_monitoring'] = monitoring_results
        except Exception as e:
            print(f"Error in real-time monitoring: {e}")
            results['analyses']['realtime_monitoring'] = {'error': str(e)}
        
        return results
    
    def _run_attribution(
        self,
        run_id: str,
        portfolio_data: Dict,
        stock_data: Optional[pd.DataFrame]
    ) -> Dict:
        """Run performance attribution analysis."""
        if stock_data is None:
            return {'error': 'Stock data required for attribution'}
        
        returns = portfolio_data.get('returns')
        weights = portfolio_data.get('weights')
        
        if returns is None or weights is None:
            return {'error': 'Portfolio returns and weights required'}
        
        # Extract stock returns from stock_data
        # Handle both DataFrame and dict formats
        if isinstance(stock_data, pd.DataFrame):
            stock_returns = stock_data.pivot_table(
                index='date', columns='ticker', values='return'
            ) if 'return' in stock_data.columns and 'date' in stock_data.columns and 'ticker' in stock_data.columns else None
        elif isinstance(stock_data, dict):
            # Try to get returns from dict
            stock_returns = stock_data.get('returns')
            if stock_returns is None and 'data' in stock_data:
                data = stock_data['data']
                if isinstance(data, pd.DataFrame) and 'return' in data.columns:
                    stock_returns = data.pivot_table(
                        index='date', columns='ticker', values='return'
                    ) if 'date' in data.columns and 'ticker' in data.columns else None
        else:
            stock_returns = None
        
        if stock_returns is None:
            return {
                'error': 'Stock returns not found in stock_data',
                'missing_data': ['stock_returns'],
                'fix_instructions': [
                    'Stock returns are needed for performance attribution. '
                    'These can be calculated from price data or loaded from backtest results. '
                    'The data loader needs to be enhanced to extract individual stock returns.'
                ]
            }
        
        # Normalize timezones to avoid tz-naive/tz-aware issues
        if hasattr(returns.index, 'tz') and returns.index.tz is not None:
            returns.index = returns.index.tz_localize(None)
        if hasattr(weights.index, 'tz') and weights.index.tz is not None:
            weights.index = weights.index.tz_localize(None)
        if stock_returns is not None and hasattr(stock_returns.index, 'tz') and stock_returns.index.tz is not None:
            stock_returns.index = stock_returns.index.tz_localize(None)
        
        # Run attribution
        attribution = self.attribution_analyzer.analyze(
            portfolio_returns=returns,
            portfolio_weights=weights,
            stock_returns=stock_returns,
            sector_mapping=portfolio_data.get('sector_mapping')
        )
        
        # Save to database
        start_date = portfolio_data.get('start_date', returns.index[0])
        end_date = portfolio_data.get('end_date', returns.index[-1])
        
        self.service.save_performance_attribution(
            run_id=run_id,
            start_date=start_date,
            end_date=end_date,
            total_return=attribution['total_return'],
            attributions={
                'factor': attribution['attributions'].get('factor', 0),
                'sector': attribution['attributions'].get('sector', 0),
                'stock_selection': attribution['attributions'].get('stock_selection', 0),
                'timing': attribution['attributions'].get('timing', 0),
                'interaction': attribution['attributions'].get('interaction', 0)
            },
            breakdown=attribution.get('breakdown')
        )
        
        # Save as analysis result
        self.service.save_analysis_result(
            run_id=run_id,
            analysis_type='attribution',
            results=attribution,
            summary={
                'total_return': attribution['total_return'],
                'factor_attribution': attribution['attributions'].get('factor', 0),
                'sector_attribution': attribution['attributions'].get('sector', 0),
                'stock_selection_attribution': attribution['attributions'].get('stock_selection', 0)
            }
        )
        
        return attribution
    
    def _run_benchmark_comparison(
        self,
        run_id: str,
        portfolio_data: Dict
    ) -> Dict:
        """Run benchmark comparison."""
        returns = portfolio_data.get('returns')
        if returns is None:
            return {'error': 'Portfolio returns required'}
        
        start_date = portfolio_data.get('start_date', returns.index[0])
        end_date = portfolio_data.get('end_date', returns.index[-1])
        
        # Compare against common benchmarks
        benchmarks = ['SPY', 'QQQ']
        comparisons = {}
        
        for benchmark_symbol in benchmarks:
            try:
                comparison = self.benchmark_comparator.compare(
                    portfolio_returns=returns,
                    benchmark_symbol=benchmark_symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if 'error' not in comparison:
                    # Save to database
                    self.service.save_benchmark_comparison(
                        run_id=run_id,
                        benchmark_symbol=benchmark_symbol,
                        benchmark_name=comparison.get('benchmark_name', benchmark_symbol),
                        start_date=start_date,
                        end_date=end_date,
                        portfolio_metrics=comparison['portfolio_metrics'],
                        benchmark_metrics=comparison['benchmark_metrics'],
                        relative_metrics=comparison['relative_metrics']
                    )
                
                comparisons[benchmark_symbol] = comparison
            except Exception as e:
                comparisons[benchmark_symbol] = {'error': str(e)}
        
        # Save as analysis result
        self.service.save_analysis_result(
            run_id=run_id,
            analysis_type='benchmark_comparison',
            results=comparisons,
            summary={
                'benchmarks_compared': len([c for c in comparisons.values() if 'error' not in c]),
                'avg_alpha': np.mean([c.get('relative_metrics', {}).get('alpha', 0) 
                                     for c in comparisons.values() if 'error' not in c])
            }
        )
        
        return comparisons
    
    def _run_factor_exposure(
        self,
        run_id: str,
        portfolio_data: Dict,
        stock_data: Optional[pd.DataFrame]
    ) -> Dict:
        """Run factor exposure analysis."""
        weights = portfolio_data.get('weights')
        if weights is None:
            return {'error': 'Portfolio weights required'}
        
        # Get current weights (latest)
        if isinstance(weights, pd.DataFrame):
            current_weights = weights.iloc[-1] if len(weights) > 0 else pd.Series()
        else:
            current_weights = weights
        
        # Extract stock features from stock_data - handle both DataFrame and dict formats
        if stock_data is None:
            return {'error': 'Stock data required for factor exposure'}
        
        # Handle different data formats
        if isinstance(stock_data, pd.DataFrame):
            # DataFrame format
            feature_columns = [c for c in stock_data.columns 
                              if c not in ['date', 'ticker', 'return', 'sector']]
            
            if len(feature_columns) == 0:
                return {'error': 'No feature columns found in stock_data'}
            
            # Get latest features for each ticker
            if 'ticker' in stock_data.columns:
                stock_features = stock_data.groupby('ticker')[feature_columns].last()
            else:
                stock_features = stock_data[feature_columns]
        elif isinstance(stock_data, dict):
            # Dict format - get features or data (avoid DataFrame truth value issue)
            stock_features = stock_data.get('features')
            if stock_features is None:
                stock_features = stock_data.get('data')
            if stock_features is None:
                return {'error': 'Stock features not found in stock_data'}
            
            if not isinstance(stock_features, pd.DataFrame):
                return {'error': 'Stock features must be a DataFrame'}
            
            # Get feature columns
            feature_columns = [c for c in stock_features.columns 
                              if c not in ['date', 'ticker', 'return', 'sector']]
            
            if len(feature_columns) == 0:
                return {'error': 'No feature columns found in stock_features'}
            
            # Get latest features for each ticker
            if 'ticker' in stock_features.columns:
                stock_features = stock_features.groupby('ticker')[feature_columns].last()
            else:
                stock_features = stock_features[feature_columns]
        else:
            return {'error': 'Invalid stock_data format'}
        
        # Validate stock_features is a DataFrame
        if not isinstance(stock_features, pd.DataFrame):
            return {'error': 'Stock features must be a DataFrame after processing'}
        
        if stock_features.empty:
            return {'error': 'Stock features DataFrame is empty'}
        
        # Run factor analysis
        factor_results = self.factor_analyzer.analyze(
            portfolio_weights=current_weights,
            stock_features=stock_features
        )
        
        # Save to database
        self.service.save_factor_exposures(
            run_id=run_id,
            factor_exposures=factor_results['factor_exposures']
        )
        
        # Save as analysis result
        self.service.save_analysis_result(
            run_id=run_id,
            analysis_type='factor_exposure',
            results=factor_results,
            summary={
                'total_factors': factor_results['total_factors'],
                'top_factors': [f['factor_name'] for f in 
                               sorted(factor_results['factor_exposures'], 
                                     key=lambda x: abs(x['exposure']), 
                                     reverse=True)[:5]]
            }
        )
        
        return factor_results
    
    def _run_rebalancing_analysis(
        self,
        run_id: str,
        portfolio_data: Dict
    ) -> Dict:
        """Run rebalancing analysis."""
        weights = portfolio_data.get('weights')
        if weights is None:
            return {'error': 'Portfolio weights required'}
        
        rebalancing = self.rebalancing_analyzer.analyze(
            portfolio_weights=weights
        )
        
        if 'error' not in rebalancing:
            # Save to database
            self.service.save_analysis_result(
                run_id=run_id,
                analysis_type='rebalancing',
                results=rebalancing,
                summary={
                    'current_drift': rebalancing.get('drift_analysis', {}).get('current_drift', 0),
                    'should_rebalance': rebalancing.get('recommendations', {}).get('should_rebalance', False),
                    'total_cost': rebalancing.get('cost_analysis', {}).get('total_transaction_cost', 0)
                }
            )
        
        return rebalancing
    
    def _run_style_analysis(
        self,
        run_id: str,
        portfolio_data: Dict,
        stock_data: Optional[pd.DataFrame]
    ) -> Dict:
        """Run style analysis."""
        weights = portfolio_data.get('weights')
        if weights is None:
            return {'error': 'Portfolio weights required'}
        
        # Get current weights
        if isinstance(weights, pd.DataFrame):
            current_weights = weights.iloc[-1] if len(weights) > 0 else pd.Series()
        else:
            current_weights = weights
        
        # Get stock features - handle dict or DataFrame
        if stock_data is None:
            return {'error': 'Stock data required for style analysis'}
        
        # Extract DataFrame from dict if needed
        if isinstance(stock_data, dict):
            # Try to get features DataFrame
            if 'features' in stock_data and isinstance(stock_data['features'], pd.DataFrame):
                stock_features_df = stock_data['features']
            elif 'data' in stock_data and isinstance(stock_data['data'], pd.DataFrame):
                stock_features_df = stock_data['data']
            else:
                return {'error': 'Stock features DataFrame not found in stock_data dict'}
        elif isinstance(stock_data, pd.DataFrame):
            stock_features_df = stock_data
        else:
            return {'error': f'Unexpected stock_data type: {type(stock_data)}'}
        
        # Extract features - handle different data formats
        if 'ticker' in stock_features_df.columns:
            # Long format: group by ticker
            feature_columns = [c for c in stock_features_df.columns 
                              if c not in ['date', 'ticker', 'return', 'sector']]
            if len(feature_columns) > 0:
                stock_features = stock_features_df.groupby('ticker')[feature_columns].last()
            else:
                return {'error': 'No feature columns found in stock data'}
        else:
            # Wide format: already indexed by ticker
            feature_columns = [c for c in stock_features_df.columns 
                              if c not in ['date', 'return', 'sector']]
            stock_features = stock_features_df[feature_columns] if len(feature_columns) > 0 else stock_features_df
        
        style = self.style_analyzer.analyze(
            portfolio_weights=current_weights,
            stock_features=stock_features
        )
        
        if 'error' not in style:
            # Save to database
            overall_style = f"{style.get('growth_value', {}).get('classification', 'Unknown')} {style.get('size', {}).get('classification', 'Unknown')}"
            self.service.save_analysis_result(
                run_id=run_id,
                analysis_type='style',
                results=style,
                summary={
                    'overall_style': overall_style,
                    'growth_value': style.get('growth_value', {}).get('classification', 'unknown'),
                    'size': style.get('size', {}).get('classification', 'unknown')
                }
            )
        
        return style
    
    def _run_ai_insights(
        self,
        run_id: str,
        portfolio_data: Dict,
        stock_data: Optional[pd.DataFrame]
    ) -> Dict:
        """Generate and save AI insights."""
        # AI insights are typically generated separately via the AI Insights page
        # This method can be used to trigger generation if needed
        # For now, just check if insights exist
        insights = self.service.get_all_ai_insights(run_id)
        return {
            'status': 'completed' if insights else 'not_generated',
            'count': len(insights),
            'types': [i.insight_type for i in insights]
        }
    
    def _run_event_analysis(
        self,
        run_id: str,
        portfolio_data: Dict,
        stock_data: Optional[pd.DataFrame]
    ) -> Dict:
        """Run event-driven analysis."""
        returns = portfolio_data.get('returns')
        if returns is None:
            return {'error': 'Portfolio returns required'}
        
        holdings = portfolio_data.get('holdings', [])
        benchmark_returns = portfolio_data.get('benchmark_returns')
        
        event_results = self.event_analyzer.analyze_portfolio_events(
            portfolio_returns=returns,
            tickers=holdings,
            benchmark_returns=benchmark_returns
        )
        
        if 'error' not in event_results:
            self.service.save_analysis_result(
                run_id=run_id,
                analysis_type='event_analysis',
                results=event_results,
                summary={
                    'total_events': event_results.get('summary', {}).get('total_events_analyzed', 0),
                    'avg_event_return': event_results.get('summary', {}).get('avg_event_return', 0)
                }
            )
        
        return event_results
    
    def _run_tax_optimization(
        self,
        run_id: str,
        portfolio_data: Dict,
        stock_data: Optional[pd.DataFrame]
    ) -> Dict:
        """Run tax optimization analysis."""
        weights = portfolio_data.get('weights')
        if weights is None or len(weights) == 0:
            return {'error': 'Portfolio weights required'}
        
        # Get latest weights and positions
        latest_weights = weights.iloc[-1] if hasattr(weights, 'iloc') else weights
        positions = pd.DataFrame({
            'ticker': latest_weights.index,
            'shares': [1.0] * len(latest_weights)  # Placeholder - would need actual shares
        })
        
        # Placeholder for cost basis and current prices
        # In production, these would come from trade history and market data
        cost_basis = {ticker: 100.0 for ticker in latest_weights.index}
        current_prices = {ticker: 100.0 for ticker in latest_weights.index}
        
        # Tax-loss harvesting suggestions
        harvest_suggestions = self.tax_optimizer.suggest_tax_loss_harvesting(
            positions=positions,
            current_prices=current_prices,
            cost_basis=cost_basis
        )
        
        # Turnover for tax efficiency
        turnover_results = self.turnover_analyzer.calculate_turnover(weights)
        turnover_by_period = {'annual': turnover_results.get('statistics', {}).get('annualized_turnover', 0)}
        
        # Tax efficiency analysis
        tax_efficiency = self.tax_optimizer.analyze_tax_efficiency(
            portfolio_returns=portfolio_data.get('returns'),
            trades=pd.DataFrame(),  # Would need actual trade history
            turnover_by_period=turnover_by_period
        )
        
        tax_results = {
            'harvest_suggestions': harvest_suggestions,
            'tax_efficiency': tax_efficiency,
            'turnover': turnover_results
        }
        
        self.service.save_analysis_result(
            run_id=run_id,
            analysis_type='tax_optimization',
            results=tax_results,
            summary={
                'harvestable_loss': harvest_suggestions.get('total_harvestable_loss', 0),
                'tax_efficiency_score': tax_efficiency.get('turnover_analysis', {}).get('tax_efficiency_score', 0)
            }
        )
        
        return tax_results
    
    def _run_monte_carlo(
        self,
        run_id: str,
        portfolio_data: Dict
    ) -> Dict:
        """Run Monte Carlo simulation."""
        returns = portfolio_data.get('returns')
        if returns is None or len(returns) < 30:
            return {'error': 'Insufficient historical returns (need at least 30 observations)'}
        
        mc_results = self.monte_carlo.simulate_portfolio_returns(
            historical_returns=returns,
            num_simulations=10000,
            time_horizon_days=252,
            method='bootstrap'
        )
        
        if 'error' not in mc_results:
            self.service.save_analysis_result(
                run_id=run_id,
                analysis_type='monte_carlo',
                results=mc_results,
                summary={
                    'expected_return': mc_results.get('simulation_stats', {}).get('mean', 0),
                    'var_95': mc_results.get('value_at_risk', {}).get('var_95', 0),
                    'prob_positive': mc_results.get('probability_metrics', {}).get('prob_positive_return', 0)
                }
            )
        
        return mc_results
    
    def _run_turnover_analysis(
        self,
        run_id: str,
        portfolio_data: Dict
    ) -> Dict:
        """Run turnover and churn analysis."""
        weights = portfolio_data.get('weights')
        if weights is None:
            return {'error': 'Portfolio weights required'}
        
        turnover = self.turnover_analyzer.calculate_turnover(weights)
        churn = self.turnover_analyzer.calculate_churn_rate(weights)
        holding_periods = self.turnover_analyzer.analyze_holding_periods(weights)
        stability = self.turnover_analyzer.calculate_position_stability(weights)
        
        turnover_results = {
            'turnover': turnover,
            'churn': churn,
            'holding_periods': holding_periods,
            'stability': stability
        }
        
        self.service.save_analysis_result(
            run_id=run_id,
            analysis_type='turnover',
            results=turnover_results,
            summary={
                'annualized_turnover': turnover.get('statistics', {}).get('annualized_turnover', 0),
                'mean_churn_rate': churn.get('statistics', {}).get('mean_churn_rate', 0),
                'avg_holding_period': holding_periods.get('statistics', {}).get('mean_holding_period_days', 0)
            }
        )
        
        return turnover_results
    
    def _run_earnings_analysis(
        self,
        run_id: str,
        portfolio_data: Dict,
        stock_data: Optional[pd.DataFrame]
    ) -> Dict:
        """Run earnings calendar analysis."""
        weights = portfolio_data.get('weights')
        holdings = portfolio_data.get('holdings', [])
        
        if weights is None or len(holdings) == 0:
            return {'error': 'Portfolio weights and holdings required'}
        
        # Fetch earnings dates
        earnings_dates = self.earnings_analyzer.fetch_earnings_dates(
            tickers=holdings,
            start_date=weights.index[0] if hasattr(weights, 'index') else None,
            end_date=weights.index[-1] if hasattr(weights, 'index') else None
        )
        
        # Analyze exposure
        exposure = self.earnings_analyzer.analyze_portfolio_earnings_exposure(
            portfolio_weights=weights,
            earnings_dates=earnings_dates
        )
        
        # Analyze impact if stock returns available
        impact = None
        if stock_data is not None:
            if isinstance(stock_data, dict):
                stock_returns = stock_data.get('returns')
            else:
                stock_returns = stock_data
            
            if stock_returns is not None and isinstance(stock_returns, pd.DataFrame):
                impact = self.earnings_analyzer.analyze_portfolio_earnings_impact(
                    portfolio_weights=weights,
                    stock_returns=stock_returns,
                    earnings_dates=earnings_dates
                )
        
        earnings_results = {
            'earnings_dates': {k: [d.isoformat() if isinstance(d, datetime) else str(d) for d in v] 
                              for k, v in earnings_dates.items()},
            'exposure': exposure,
            'impact': impact
        }
        
        self.service.save_analysis_result(
            run_id=run_id,
            analysis_type='earnings',
            results=earnings_results,
            summary={
                'upcoming_earnings_count': exposure.get('count', 0) if 'error' not in exposure else 0,
                'total_exposure': exposure.get('total_exposure', 0) if 'error' not in exposure else 0
            }
        )
        
        return earnings_results
    
    def _run_realtime_monitoring(
        self,
        run_id: str,
        portfolio_data: Dict,
        stock_data: Optional[pd.DataFrame]
    ) -> Dict:
        """Run real-time monitoring."""
        returns = portfolio_data.get('returns')
        weights = portfolio_data.get('weights')
        
        if returns is None or weights is None:
            return {'error': 'Portfolio returns and weights required'}
        
        # Extract stock returns if available
        stock_returns = None
        if stock_data is not None:
            if isinstance(stock_data, dict):
                stock_returns = stock_data.get('returns')
            elif isinstance(stock_data, pd.DataFrame):
                stock_returns = stock_data
        
        # Generate alerts
        alerts = self.realtime_monitor.check_portfolio_alerts(
            portfolio_returns=returns,
            portfolio_weights=weights,
            stock_returns=stock_returns,
            benchmark_returns=portfolio_data.get('benchmark_returns')
        )
        
        # Daily summary
        summary = self.realtime_monitor.generate_daily_summary(
            portfolio_returns=returns,
            portfolio_weights=weights,
            benchmark_returns=portfolio_data.get('benchmark_returns')
        )
        
        # Performance metrics
        metrics = self.realtime_monitor.track_performance_metrics(
            portfolio_returns=returns,
            period_days=30
        )
        
        monitoring_results = {
            'alerts': alerts,
            'daily_summary': summary,
            'performance_metrics': metrics
        }
        
        self.service.save_analysis_result(
            run_id=run_id,
            analysis_type='realtime_monitoring',
            results=monitoring_results,
            summary={
                'alert_count': len(alerts),
                'critical_alerts': len([a for a in alerts if a.get('level') == 'critical']),
                'daily_return': summary.get('daily_return', 0) if 'error' not in summary else 0
            }
        )
        
        return monitoring_results


def load_portfolio_data_from_run(run_dir: Path) -> Dict[str, Any]:
    """Load portfolio data from a run directory."""
    from .data_loader import RunDataLoader
    
    try:
        loader = RunDataLoader(run_dir)
        return loader.load_portfolio_data()
    except Exception as e:
        return {'error': str(e)}
