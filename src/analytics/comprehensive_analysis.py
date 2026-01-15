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
        completeness = self.data_checker.check_data_completeness(
            portfolio_data,
            stock_data if stock_data is not None else {},
            benchmark_data=None  # Will be checked during benchmark comparison
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
        
        # 1. Performance Attribution
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
        benchmark_status = completeness['analysis_status'].get('benchmark_comparison', {})
        if benchmark_status.get('can_run', False):
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
        else:
            print(f"⚠️  Skipping benchmark comparison: {benchmark_status.get('message', 'Missing required data')}")
            results['analyses']['benchmark'] = {
                'error': benchmark_status.get('message', 'Missing required data'),
                'skipped': True,
                'missing_data': benchmark_status.get('missing', [])
            }
        
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
        
        # Get stock features
        if stock_data is None:
            return {'error': 'Stock data required for style analysis'}
        
        # Extract features - handle different data formats
        if 'ticker' in stock_data.columns:
            # Long format: group by ticker
            feature_columns = [c for c in stock_data.columns 
                              if c not in ['date', 'ticker', 'return', 'sector']]
            if len(feature_columns) > 0:
                stock_features = stock_data.groupby('ticker')[feature_columns].last()
            else:
                return {'error': 'No feature columns found in stock data'}
        else:
            # Wide format: already indexed by ticker
            feature_columns = [c for c in stock_data.columns 
                              if c not in ['date', 'return', 'sector']]
            stock_features = stock_data[feature_columns] if len(feature_columns) > 0 else stock_data
        
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


def load_portfolio_data_from_run(run_dir: Path) -> Dict[str, Any]:
    """Load portfolio data from a run directory."""
    from .data_loader import RunDataLoader
    
    try:
        loader = RunDataLoader(run_dir)
        return loader.load_portfolio_data()
    except Exception as e:
        return {'error': str(e)}
