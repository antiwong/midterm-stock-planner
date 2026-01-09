#!/usr/bin/env python3
"""
Full Analysis Workflow
======================
Runs the complete analysis pipeline:

1. NUMERIC ANALYSIS (Primary - Always Run)
   - Portfolio enrichment (scores, weights, risk contributions)
   - Vertical analysis (within-sector ranking)
   - Horizontal analysis (cross-sector portfolio construction)
   
2. GEMINI COMMENTARY (Optional - Only if requested)
   - Explain patterns in the numeric data
   - Highlight concentration risks
   - Generate natural-language summaries

Usage:
    # Numeric only (default)
    python scripts/full_analysis_workflow.py
    
    # With optional Gemini commentary
    python scripts/full_analysis_workflow.py --with-commentary
    
    # Specific run
    python scripts/full_analysis_workflow.py --run-id 20241231_123456_abc
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import yaml


def run_workflow(
    run_id: str = None,
    config_path: str = "config/config.yaml",
    output_dir: str = "output",
    with_commentary: bool = False,
    with_recommendations: bool = False,
    watchlist: str = None,
    skip_validation: bool = False,
    start_date: str = None,
    end_date: str = None,
):
    """
    Run the full analysis workflow.
    
    Args:
        run_id: Specific run ID or None for latest
        config_path: Path to config file
        output_dir: Output directory (run folder will be created inside)
        with_commentary: Whether to generate Gemini commentary
        with_recommendations: Whether to generate AI portfolio recommendations
        watchlist: Filter to specific watchlist (e.g., 'tech_giants')
        skip_validation: Whether to skip data validation step
        start_date: Start date for data validation (YYYY-MM-DD)
        end_date: End date for data validation (YYYY-MM-DD)
    """
    # Load watchlist info if specified
    watchlist_display_name = None
    watchlist_symbols = []
    if watchlist:
        from src.data.watchlists import WatchlistManager
        wl_manager = WatchlistManager.from_config_dir("config")
        wl = wl_manager.get_watchlist(watchlist)
        if wl:
            watchlist_display_name = wl.name
            watchlist_symbols = wl.symbols
        else:
            print(f"Warning: Watchlist '{watchlist}' not found")
            watchlist = None
    
    print("=" * 70)
    print("FULL ANALYSIS WORKFLOW")
    print("=" * 70)
    print(f"Config: {config_path}")
    print(f"Base Output: {output_dir}")
    print(f"Watchlist: {watchlist_display_name or 'All (from run)'}")
    if start_date or end_date:
        date_range = f"{start_date or 'auto'} to {end_date or 'auto'}"
        print(f"Date Range: {date_range}")
    print(f"Commentary: {'Yes' if with_commentary else 'No'}")
    print(f"Recommendations: {'Yes' if with_recommendations else 'No'}")
    print(f"Data Validation: {'Skip' if skip_validation else 'Yes'}")
    print("=" * 70)
    
    # Load config
    config_path = Path(config_path)
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        config = {}
    
    base_output = Path(output_dir)
    base_output.mkdir(parents=True, exist_ok=True)
    
    # Track validation results for report
    validation_report = None
    
    # =========================================================================
    # STEP 0: Data Validation (Pre-flight Check)
    # =========================================================================
    if not skip_validation and watchlist_symbols:
        print("\n" + "=" * 70)
        print("STEP 0: DATA VALIDATION (Pre-flight Check)")
        print("=" * 70)
        
        try:
            from scripts.download_prices import DataValidator
            
            price_path = Path("data/prices.csv")
            if price_path.exists():
                price_df = pd.read_csv(price_path, parse_dates=['date'])
                
                # Use provided dates or default to 3 years
                validation_end_date = end_date or datetime.now().strftime('%Y-%m-%d')
                validation_start_date = start_date or (datetime.now() - pd.Timedelta(days=3*365)).strftime('%Y-%m-%d')
                
                validator = DataValidator(
                    price_df=price_df,
                    required_tickers=watchlist_symbols,
                    start_date=validation_start_date,
                    end_date=validation_end_date
                )
                
                validation_result = validator.validate()
                validation_report = validation_result
                
                print(f"\n{validation_result['summary']}")
                
                # Show errors
                if validation_result['errors']:
                    print("\n⚠️ DATA ISSUES DETECTED:")
                    for error in validation_result['errors']:
                        print(f"   ❌ {error['type']}: {error['message']}")
                        if error['type'] == 'MISSING_TICKERS' and error.get('details'):
                            missing = error['details'][:10]
                            print(f"      Missing: {', '.join(missing)}")
                            if len(error['details']) > 10:
                                print(f"      ... and {len(error['details']) - 10} more")
                    
                    print("\n   💡 Run: python scripts/download_prices.py --watchlist", watchlist or 'custom')
                    print("      to download missing data")
                
                # Show warnings
                if validation_result['warnings']:
                    for warning in validation_result['warnings'][:3]:
                        print(f"   ⚠️ {warning['type']}: {warning['message']}")
                
                print(f"\n   Coverage: {validation_result['stats'].get('coverage_pct', 0):.1f}% of watchlist has data")
            else:
                print("   ⚠️ No price data file found: data/prices.csv")
                print("   💡 Run: python scripts/download_prices.py --watchlist", watchlist or 'custom')
                validation_report = {
                    'valid': False,
                    'errors': [{'type': 'NO_DATA_FILE', 'message': 'prices.csv not found', 'details': None}],
                    'warnings': [],
                    'stats': {},
                    'summary': 'No price data available'
                }
        except ImportError as e:
            print(f"   ⚠️ Could not run validation: {e}")
        except Exception as e:
            print(f"   ⚠️ Validation error: {e}")
    
    # =========================================================================
    # STEP 1: Load Run Data
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 1: LOAD RUN DATA")
    print("=" * 70)
    
    from src.analytics.models import get_db, Run, StockScore
    
    db = get_db("data/analysis.db")
    session = db.get_session()
    
    try:
        if run_id:
            run = session.query(Run).filter_by(run_id=run_id).first()
        else:
            run = session.query(Run).order_by(Run.created_at.desc()).first()
        
        if not run:
            print("❌ No runs found in database")
            print("   Run a backtest first: python -m src.app.cli run-backtest")
            return 1
        
        print(f"   Run ID: {run.run_id}")
        print(f"   Name: {run.name}")
        print(f"   Status: {run.status}")
        print(f"   Created: {run.created_at}")
        
        # Use watchlist from run if not specified
        run_watchlist = watchlist or getattr(run, 'watchlist', None)
        if run_watchlist and not watchlist_display_name:
            watchlist_display_name = getattr(run, 'watchlist_display_name', run_watchlist)
        
        print(f"   Watchlist: {watchlist_display_name or 'None (default universe)'}")
        
        # Create run-specific output folder with watchlist prefix
        if run_watchlist:
            run_folder_name = f"run_{run_watchlist}_{run.run_id[:16]}"
        else:
            run_folder_name = f"run_{run.run_id[:16]}"
        output_path = base_output / run_folder_name
        output_path.mkdir(parents=True, exist_ok=True)
        output_dir = str(output_path)  # Update for downstream use
        
        print(f"   Output Folder: {output_path}")
        
        # Get scores
        scores = session.query(StockScore).filter_by(run_id=run.run_id).all()
        if not scores:
            print("❌ No stock scores found for this run")
            return 1
        
        scores_df = pd.DataFrame([s.to_dict() for s in scores])
        print(f"   Stocks: {len(scores_df)}")
        
        # Build run metrics
        run_metrics = {
            'total_return': run.total_return or 0,
            'sharpe_ratio': run.sharpe_ratio or 0,
            'max_drawdown': run.max_drawdown or 0,
            'volatility': getattr(run, 'volatility', None) or 0,
            'win_rate': run.win_rate or run.hit_rate or 0,
        }
        
    finally:
        session.close()
    
    # =========================================================================
    # STEP 2: Portfolio Enrichment
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 2: PORTFOLIO ENRICHMENT (Numeric)")
    print("=" * 70)
    
    # Import and run analyze_portfolio
    from scripts.analyze_portfolio import analyze_portfolio
    
    try:
        enriched_df, sector_analysis, summary = analyze_portfolio(
            run_id=run.run_id,
            output_dir=output_dir
        )
        print("   ✅ Portfolio enrichment complete")
    except Exception as e:
        print(f"   ⚠️ Portfolio enrichment failed: {e}")
        enriched_df = scores_df
        sector_analysis = pd.DataFrame()
        summary = {}
    
    # =========================================================================
    # STEP 3: Vertical Analysis (Within-Sector)
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 3: VERTICAL ANALYSIS (Within-Sector, Numeric)")
    print("=" * 70)
    
    from src.analysis.domain_analysis import AnalysisConfig, DomainAnalyzer
    
    analysis_config = AnalysisConfig.from_dict(config)
    analyzer = DomainAnalyzer(analysis_config, output_dir)
    
    # Load price data for returns
    price_path = Path("data/prices.csv")
    if price_path.exists():
        price_df = pd.read_csv(price_path, parse_dates=['date'])
        price_df = price_df.sort_values(['ticker', 'date'])
        price_df['return_1d'] = price_df.groupby('ticker')['close'].pct_change()
        returns_df = price_df[['date', 'ticker', 'return_1d']]
    else:
        returns_df = None
    
    # Run vertical analysis
    try:
        vertical_results = analyzer.run_vertical_analysis(
            df=scores_df,
            date=datetime.now(),
            model_scores=None
        )
        
        total_candidates = sum(len(r.candidates) for r in vertical_results.values())
        total_filtered = sum(len(r.filtered_out) for r in vertical_results.values())
        print(f"   Sectors analyzed: {len(vertical_results)}")
        print(f"   Total candidates: {total_candidates}")
        print(f"   Filtered out: {total_filtered}")
        print("   ✅ Vertical analysis complete")
        
    except Exception as e:
        print(f"   ⚠️ Vertical analysis failed: {e}")
        vertical_results = {}
    
    # =========================================================================
    # STEP 4: Horizontal Analysis (Cross-Sector Portfolio)
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 4: HORIZONTAL ANALYSIS (Cross-Sector Portfolio, Numeric)")
    print("=" * 70)
    
    try:
        if vertical_results:
            horizontal_result = analyzer.run_horizontal_analysis(
                vertical_results=vertical_results,
                returns_df=returns_df,
                date=datetime.now()
            )
            
            print(f"   Portfolio size: {len(horizontal_result.portfolio)}")
            print(f"   Selection method: {analysis_config.selection_method}")
            
            if horizontal_result.risk_metrics:
                print("\n   Risk Metrics:")
                for metric, value in horizontal_result.risk_metrics.items():
                    if isinstance(value, float):
                        if 'ratio' in metric.lower():
                            print(f"      {metric}: {value:.2f}")
                        else:
                            print(f"      {metric}: {value:.4f}")
            
            print("\n   Constraint Status:")
            for constraint, satisfied in horizontal_result.constraints_satisfied.items():
                status = "✅ PASS" if satisfied else "❌ FAIL"
                print(f"      {constraint}: {status}")
            
            print("   ✅ Horizontal analysis complete")
        else:
            print("   ⚠️ Skipped - no vertical results")
            horizontal_result = None
            
    except Exception as e:
        print(f"   ⚠️ Horizontal analysis failed: {e}")
        horizontal_result = None
    
    # =========================================================================
    # STEP 5: Generate Summary Report
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 5: GENERATE SUMMARY REPORT")
    print("=" * 70)
    
    import json
    
    report = {
        'run_id': run.run_id,
        'run_name': run.name,
        'generated_at': datetime.now().isoformat(),
        'workflow_steps': {
            'data_validation': validation_report is not None,
            'portfolio_enrichment': len(enriched_df) > 0,
            'vertical_analysis': len(vertical_results) > 0,
            'horizontal_analysis': horizontal_result is not None,
        },
        'run_metrics': run_metrics,
        'portfolio_summary': summary,
    }
    
    # Add data validation section if available
    if validation_report:
        report['data_validation'] = {
            'status': 'PASSED' if validation_report.get('valid', False) else 'FAILED',
            'coverage_pct': validation_report.get('stats', {}).get('coverage_pct', 0),
            'available_tickers': validation_report.get('stats', {}).get('available_tickers', 0),
            'missing_tickers': validation_report.get('stats', {}).get('missing_tickers', 0),
            'errors': [e['message'] for e in validation_report.get('errors', [])],
            'warnings': [w['message'] for w in validation_report.get('warnings', [])][:5],
        }
    
    if horizontal_result and len(horizontal_result.portfolio) > 0:
        report['portfolio'] = {
            'n_holdings': len(horizontal_result.portfolio),
            'risk_metrics': horizontal_result.risk_metrics,
            'constraints': horizontal_result.constraints_satisfied,
            'holdings': horizontal_result.portfolio[
                ['ticker', 'sector', 'weight', 'domain_score']
            ].to_dict('records') if all(c in horizontal_result.portfolio.columns 
                                        for c in ['ticker', 'sector', 'weight', 'domain_score']) 
            else []
        }
    
    report_path = output_path / f"analysis_report_{run.run_id[:16]}.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"   Report saved: {report_path}")
    print("   ✅ Summary report complete")
    
    # =========================================================================
    # STEP 6: Optional Gemini Commentary
    # =========================================================================
    if with_commentary:
        print("\n" + "=" * 70)
        print("STEP 6: GEMINI COMMENTARY (Optional)")
        print("=" * 70)
        print("   NOTE: Commentary is READ-ONLY - explains but doesn't change analysis")
        
        from src.analysis.gemini_commentary import (
            generate_portfolio_commentary,
            generate_risk_commentary,
            save_commentary_to_file,
            get_gemini_client,
        )
        
        client = get_gemini_client()
        if client is None:
            print("   ⚠️ Gemini API not available - skipping commentary")
        else:
            try:
                # Generate portfolio commentary
                if horizontal_result and len(horizontal_result.portfolio) > 0:
                    portfolio_df = horizontal_result.portfolio
                    metrics = horizontal_result.risk_metrics
                else:
                    portfolio_df = scores_df
                    metrics = run_metrics
                
                print("   Generating portfolio commentary...")
                commentary = generate_portfolio_commentary(
                    portfolio_df=portfolio_df,
                    metrics=metrics,
                    sector_breakdown=sector_analysis if len(sector_analysis) > 0 else None,
                )
                
                if commentary:
                    filepath = save_commentary_to_file(
                        commentary, run.run_id, output_dir, "portfolio"
                    )
                    print(f"   ✅ Commentary saved: {filepath}")
                    
                    # Print preview
                    print("\n   --- Commentary Preview ---")
                    preview = commentary[:500] + "..." if len(commentary) > 500 else commentary
                    for line in preview.split('\n')[:10]:
                        print(f"   {line}")
                    print("   --- End Preview ---")
                else:
                    print("   ⚠️ Failed to generate commentary")
                    
            except Exception as e:
                print(f"   ⚠️ Commentary generation failed: {e}")
    else:
        print("\n" + "=" * 70)
        print("STEP 6: GEMINI COMMENTARY - Skipped (use --with-commentary to enable)")
        print("=" * 70)
    
    # =========================================================================
    # STEP 7: Portfolio Recommendations (Optional)
    # =========================================================================
    if with_recommendations:
        print("\n" + "=" * 70)
        print("STEP 7: PORTFOLIO RECOMMENDATIONS (AI-Powered)")
        print("=" * 70)
        print("   Generating Conservative, Balanced, and Aggressive portfolios...")
        
        from src.analysis.gemini_commentary import (
            generate_portfolio_recommendations,
            save_recommendations_to_file,
            get_gemini_client,
        )
        
        client = get_gemini_client()
        if client is None:
            print("   ⚠️ Gemini API not available - skipping recommendations")
        else:
            try:
                # Prepare horizontal result as dict
                horizontal_dict = {}
                if horizontal_result:
                    horizontal_dict = {
                        'portfolio': horizontal_result.portfolio if hasattr(horizontal_result, 'portfolio') else pd.DataFrame(),
                        'risk_metrics': horizontal_result.risk_metrics if hasattr(horizontal_result, 'risk_metrics') else {},
                        'constraints_satisfied': horizontal_result.constraints_satisfied if hasattr(horizontal_result, 'constraints_satisfied') else {},
                    }
                
                print("   Calling Gemini for portfolio recommendations...")
                recommendations = generate_portfolio_recommendations(
                    vertical_results=vertical_results,
                    horizontal_result=horizontal_dict,
                    backtest_metrics=run_metrics,
                    all_candidates=enriched_df,
                )
                
                if recommendations:
                    filepath = save_recommendations_to_file(
                        recommendations, run.run_id, output_dir
                    )
                    print(f"   ✅ Recommendations saved: {filepath}")
                    
                    # Print summary
                    recs = recommendations.get('recommendations', {})
                    if recs:
                        print("\n   --- Recommendations Summary ---")
                        for profile in ['conservative', 'balanced', 'aggressive']:
                            if profile in recs:
                                rec = recs[profile]
                                print(f"\n   📊 {profile.upper()}:")
                                print(f"      Time Horizon: {rec.get('time_horizon', 'N/A')}")
                                print(f"      Target Vol: {rec.get('target_volatility', 'N/A')}")
                                holdings = rec.get('holdings', [])[:5]
                                tickers = [h.get('ticker', '?') for h in holdings]
                                print(f"      Top Holdings: {', '.join(tickers)}")
                                expected = rec.get('expected_return', {})
                                print(f"      Expected Return: {expected.get('low', '?')}-{expected.get('high', '?')}%")
                        print("   --- End Summary ---")
                    else:
                        print("   ⚠️ Could not parse structured recommendations")
                        if recommendations.get('raw_response'):
                            print("\n   Raw response preview:")
                            preview = recommendations['raw_response'][:500]
                            for line in preview.split('\n')[:10]:
                                print(f"   {line}")
                else:
                    print("   ⚠️ Failed to generate recommendations")
                    
            except Exception as e:
                print(f"   ⚠️ Recommendations generation failed: {e}")
                import traceback
                traceback.print_exc()
    else:
        print("\n" + "=" * 70)
        print("STEP 7: RECOMMENDATIONS - Skipped (use --with-recommendations to enable)")
        print("=" * 70)
    
    # =========================================================================
    # STEP 8: AUTOMATED SAFEGUARDS VALIDATION
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 8: AUTOMATED SAFEGUARDS VALIDATION")
    print("=" * 70)
    
    try:
        from src.validation.safeguards import validate_backtest_run, RISK_PROFILE_BOUNDS
        
        # Determine risk profile from config or default to moderate
        analysis_config = config.get('analysis', {})
        horizontal_config = analysis_config.get('horizontal', {})
        risk_profile = horizontal_config.get('risk_profile', 'moderate')
        
        print(f"   Validating against '{risk_profile}' risk profile...")
        bounds = RISK_PROFILE_BOUNDS.get(risk_profile, RISK_PROFILE_BOUNDS['moderate'])
        print(f"   Limits: Vol<{bounds['max_volatility']*100:.0f}%, DD>{bounds['max_drawdown']*100:.0f}%, Sector<{bounds['max_sector_weight']*100:.0f}%")
        print()
        
        validation_report = validate_backtest_run(
            run_dir=output_path,
            config=config,
            risk_profile=risk_profile,
            strict=False  # Don't fail the workflow, just report
        )
        
        # Display results
        critical_failures = []
        warnings = []
        
        for check in validation_report.checks:
            if check.passed:
                print(f"   ✅ {check.check_name}: {check.message}")
            elif check.severity == "error":
                print(f"   ❌ {check.check_name}: {check.message}")
                critical_failures.append(check)
            else:
                print(f"   ⚠️  {check.check_name}: {check.message}")
                warnings.append(check)
        
        print()
        if critical_failures:
            print(f"   ❌ VALIDATION FAILED: {len(critical_failures)} critical issue(s)")
            print(f"   ⚠️  Do NOT use this run for recommendations until issues are fixed.")
            report['validation'] = {
                'status': 'FAILED',
                'critical_failures': len(critical_failures),
                'warnings': len(warnings)
            }
        elif warnings:
            print(f"   ⚠️  VALIDATION PASSED with {len(warnings)} warning(s)")
            print(f"   Review warnings before using for {risk_profile} recommendations.")
            report['validation'] = {
                'status': 'PASSED_WITH_WARNINGS',
                'warnings': len(warnings)
            }
        else:
            print(f"   ✅ VALIDATION PASSED - Safe for {risk_profile} recommendations")
            report['validation'] = {'status': 'PASSED'}
        
    except ImportError:
        print("   ⚠️  Validation module not available, skipping safeguards")
        report['validation'] = {'status': 'SKIPPED'}
    except Exception as e:
        print(f"   ⚠️  Validation error: {e}")
        report['validation'] = {'status': 'ERROR', 'error': str(e)}
    
    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("WORKFLOW COMPLETE")
    print("=" * 70)
    print(f"\n📁 Output files in: {output_dir}/")
    print(f"   - portfolio_enriched_*.csv      (enriched holdings)")
    print(f"   - sector_analysis_*.csv         (sector breakdown)")
    print(f"   - vertical_candidates_*.csv     (per-sector candidates)")
    print(f"   - portfolio_candidates_*.csv    (final portfolio)")
    print(f"   - portfolio_metrics_*.json      (risk metrics)")
    print(f"   - analysis_report_*.json        (full report)")
    print(f"   - validation_report.json        (safeguards validation)")
    if with_commentary:
        print(f"   - commentary_*.md               (AI commentary)")
    if with_recommendations:
        print(f"   - recommendations_*.md          (portfolio recommendations)")
        print(f"   - recommendations_*.json        (structured recommendations)")
    
    print(f"\n📊 View in dashboard: streamlit run src/app/dashboard.py")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Run full analysis workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run numeric analysis only (recommended)
  python scripts/full_analysis_workflow.py
  
  # Add optional Gemini commentary
  python scripts/full_analysis_workflow.py --with-commentary
  
  # Generate portfolio recommendations (Conservative/Balanced/Aggressive)
  python scripts/full_analysis_workflow.py --with-recommendations
  
  # Full AI analysis (commentary + recommendations)
  python scripts/full_analysis_workflow.py --with-commentary --with-recommendations
  
  # Analyze a specific run
  python scripts/full_analysis_workflow.py --run-id 20241231_123456_abc

Note: AI features (commentary, recommendations) are OPTIONAL.
      All portfolio decisions are made through numeric analysis first.
        """
    )
    parser.add_argument("--run-id", type=str, help="Specific run ID (default: latest)")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="Config file")
    parser.add_argument("--output", type=str, default="output", help="Output directory")
    parser.add_argument("--watchlist", "-w", type=str, 
                        help="Watchlist to filter analysis (e.g., tech_giants). See config/watchlists.yaml")
    parser.add_argument("--with-commentary", action="store_true", 
                        help="Generate optional Gemini commentary (explanation only)")
    parser.add_argument("--with-recommendations", action="store_true",
                        help="Generate AI portfolio recommendations (Conservative/Balanced/Aggressive)")
    parser.add_argument("--skip-validation", action="store_true",
                        help="Skip data validation step")
    parser.add_argument("--start-date", type=str,
                        help="Start date for data validation (YYYY-MM-DD). Overrides config.")
    parser.add_argument("--end-date", type=str,
                        help="End date for data validation (YYYY-MM-DD). Overrides config.")
    
    args = parser.parse_args()
    
    return run_workflow(
        run_id=args.run_id,
        config_path=args.config,
        output_dir=args.output,
        with_commentary=args.with_commentary,
        with_recommendations=args.with_recommendations,
        watchlist=args.watchlist,
        skip_validation=args.skip_validation,
        start_date=args.start_date,
        end_date=args.end_date,
    )


if __name__ == "__main__":
    sys.exit(main())
