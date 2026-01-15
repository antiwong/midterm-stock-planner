#!/usr/bin/env python3
"""
Validate Export and Visualization Features
===========================================
Test export capabilities, enhanced visualizations, and comparison tools.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime
import tempfile
import os

def test_imports():
    """Test that all required modules can be imported."""
    print("=" * 60)
    print("Testing Imports")
    print("=" * 60)
    
    errors = []
    
    # Test export module
    try:
        from src.app.dashboard.export import export_to_pdf, export_to_excel
        print("✅ Export module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import export module: {e}")
        errors.append(f"Export module: {e}")
    
    # Test enhanced charts
    try:
        from src.app.dashboard.components.enhanced_charts import (
            create_attribution_waterfall,
            create_factor_exposure_heatmap,
            create_comparison_chart,
            create_multi_metric_comparison,
            create_time_period_comparison
        )
        print("✅ Enhanced charts module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import enhanced charts: {e}")
        errors.append(f"Enhanced charts: {e}")
    
    # Test advanced comparison
    try:
        from src.app.dashboard.pages.advanced_comparison import render_advanced_comparison
        print("✅ Advanced comparison module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import advanced comparison: {e}")
        errors.append(f"Advanced comparison: {e}")
    
    # Test dependencies
    try:
        import reportlab
        print("✅ reportlab available")
    except ImportError:
        print("⚠️  reportlab not installed (PDF export will not work)")
        errors.append("reportlab not installed")
    
    try:
        import openpyxl
        print("✅ openpyxl available")
    except ImportError:
        print("⚠️  openpyxl not installed (Excel export will not work)")
        errors.append("openpyxl not installed")
    
    print()
    return errors


def test_export_functionality():
    """Test PDF and Excel export."""
    print("=" * 60)
    print("Testing Export Functionality")
    print("=" * 60)
    
    errors = []
    
    # Create sample analysis results
    sample_results = {
        'attribution': {
            'results': {
                'total_return': 0.15,
                'factor_attribution': 0.05,
                'sector_attribution': 0.04,
                'stock_selection_attribution': 0.03,
                'timing_attribution': 0.03
            }
        },
        'benchmark_comparison': {
            'results': {
                'portfolio_return': 0.15,
                'benchmark_return': 0.12,
                'alpha': 0.03,
                'portfolio_volatility': 0.18,
                'benchmark_volatility': 0.15,
                'portfolio_sharpe': 0.83,
                'benchmark_sharpe': 0.80,
                'beta': 1.05
            }
        },
        'factor_exposure': {
            'results': {
                'exposures': {
                    'Market': {'exposure': 0.95, 'contribution_to_return': 0.10, 'contribution_to_risk': 0.12},
                    'Value': {'exposure': 0.25, 'contribution_to_return': 0.02, 'contribution_to_risk': 0.03},
                    'Growth': {'exposure': -0.15, 'contribution_to_return': -0.01, 'contribution_to_risk': -0.02}
                }
            }
        },
        'rebalancing': {
            'results': {
                'current_drift': 0.05,
                'avg_turnover': 0.20,
                'total_transaction_costs': 0.002,
                'num_rebalancing_events': 12
            }
        },
        'style': {
            'results': {
                'growth_value_classification': 'Value',
                'size_classification': 'Large Cap',
                'portfolio_pe': 18.5,
                'market_pe': 20.0
            }
        }
    }
    
    sample_run_info = {
        'run_id': 'test_run_123',
        'name': 'Test Run',
        'created_at': datetime.now().isoformat(),
        'watchlist': 'test_watchlist'
    }
    
    # Test PDF export
    try:
        from src.app.dashboard.export import export_to_pdf
        pdf_bytes = export_to_pdf(sample_results, sample_run_info)
        if pdf_bytes and len(pdf_bytes) > 0:
            print(f"✅ PDF export successful ({len(pdf_bytes)} bytes)")
        else:
            print("❌ PDF export returned empty bytes")
            errors.append("PDF export returned empty")
    except ImportError as e:
        print(f"⚠️  PDF export skipped (reportlab not available): {e}")
    except Exception as e:
        print(f"❌ PDF export failed: {e}")
        errors.append(f"PDF export: {e}")
    
    # Test Excel export
    try:
        from src.app.dashboard.export import export_to_excel
        excel_bytes = export_to_excel(sample_results, sample_run_info)
        if excel_bytes and len(excel_bytes) > 0:
            print(f"✅ Excel export successful ({len(excel_bytes)} bytes)")
        else:
            print("❌ Excel export returned empty bytes")
            errors.append("Excel export returned empty")
    except ImportError as e:
        print(f"⚠️  Excel export skipped (openpyxl not available): {e}")
    except Exception as e:
        print(f"❌ Excel export failed: {e}")
        errors.append(f"Excel export: {e}")
    
    # Test file export (to temp file)
    try:
        from src.app.dashboard.export import export_to_pdf, export_to_excel
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            export_to_pdf(sample_results, sample_run_info, output_path=Path(tmp.name))
            if os.path.exists(tmp.name) and os.path.getsize(tmp.name) > 0:
                print(f"✅ PDF file export successful ({os.path.getsize(tmp.name)} bytes)")
                os.unlink(tmp.name)
            else:
                print("❌ PDF file export failed")
                errors.append("PDF file export failed")
    except ImportError:
        print("⚠️  PDF file export skipped (reportlab not available)")
    except Exception as e:
        print(f"❌ PDF file export failed: {e}")
        errors.append(f"PDF file export: {e}")
    
    try:
        from src.app.dashboard.export import export_to_excel
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            export_to_excel(sample_results, sample_run_info, output_path=Path(tmp.name))
            if os.path.exists(tmp.name) and os.path.getsize(tmp.name) > 0:
                print(f"✅ Excel file export successful ({os.path.getsize(tmp.name)} bytes)")
                os.unlink(tmp.name)
            else:
                print("❌ Excel file export failed")
                errors.append("Excel file export failed")
    except ImportError:
        print("⚠️  Excel file export skipped (openpyxl not available)")
    except Exception as e:
        print(f"❌ Excel file export failed: {e}")
        errors.append(f"Excel file export: {e}")
    
    print()
    return errors


def test_enhanced_charts():
    """Test enhanced chart creation."""
    print("=" * 60)
    print("Testing Enhanced Charts")
    print("=" * 60)
    
    errors = []
    
    try:
        from src.app.dashboard.components.enhanced_charts import create_attribution_waterfall
        
        attribution_data = {
            'factor_attribution': 0.05,
            'sector_attribution': 0.04,
            'stock_selection_attribution': 0.03,
            'timing_attribution': 0.03,
            'total_return': 0.15
        }
        
        fig = create_attribution_waterfall(attribution_data)
        if fig:
            print("✅ Attribution waterfall chart created successfully")
        else:
            print("❌ Attribution waterfall chart creation failed")
            errors.append("Attribution waterfall chart")
    except Exception as e:
        print(f"❌ Attribution waterfall chart failed: {e}")
        errors.append(f"Attribution waterfall: {e}")
    
    try:
        from src.app.dashboard.components.enhanced_charts import create_factor_exposure_heatmap
        
        factor_exposures = {
            'Market': {'exposure': 0.95, 'contribution_to_return': 0.10, 'contribution_to_risk': 0.12},
            'Value': {'exposure': 0.25, 'contribution_to_return': 0.02, 'contribution_to_risk': 0.03},
            'Growth': {'exposure': -0.15, 'contribution_to_return': -0.01, 'contribution_to_risk': -0.02}
        }
        
        fig = create_factor_exposure_heatmap(factor_exposures)
        if fig:
            print("✅ Factor exposure heatmap created successfully")
        else:
            print("❌ Factor exposure heatmap creation failed")
            errors.append("Factor exposure heatmap")
    except Exception as e:
        print(f"❌ Factor exposure heatmap failed: {e}")
        errors.append(f"Factor exposure heatmap: {e}")
    
    try:
        from src.app.dashboard.components.enhanced_charts import create_comparison_chart
        
        runs_data = [
            {'name': 'Run 1', 'run_id': 'r1', 'total_return': 0.15, 'sharpe_ratio': 0.8},
            {'name': 'Run 2', 'run_id': 'r2', 'total_return': 0.12, 'sharpe_ratio': 0.7},
            {'name': 'Run 3', 'run_id': 'r3', 'total_return': 0.18, 'sharpe_ratio': 0.9}
        ]
        
        fig = create_comparison_chart(runs_data, 'total_return')
        if fig:
            print("✅ Comparison chart created successfully")
        else:
            print("❌ Comparison chart creation failed")
            errors.append("Comparison chart")
    except Exception as e:
        print(f"❌ Comparison chart failed: {e}")
        errors.append(f"Comparison chart: {e}")
    
    try:
        from src.app.dashboard.components.enhanced_charts import create_multi_metric_comparison
        
        runs_data = [
            {'name': 'Run 1', 'total_return': 0.15, 'sharpe_ratio': 0.8, 'max_drawdown': -0.10},
            {'name': 'Run 2', 'total_return': 0.12, 'sharpe_ratio': 0.7, 'max_drawdown': -0.08}
        ]
        
        fig = create_multi_metric_comparison(runs_data, ['total_return', 'sharpe_ratio', 'max_drawdown'])
        if fig:
            print("✅ Multi-metric comparison chart created successfully")
        else:
            print("❌ Multi-metric comparison chart creation failed")
            errors.append("Multi-metric comparison")
    except Exception as e:
        print(f"❌ Multi-metric comparison failed: {e}")
        errors.append(f"Multi-metric comparison: {e}")
    
    try:
        from src.app.dashboard.components.enhanced_charts import create_time_period_comparison
        
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        returns_data = {
            'Full Period': pd.Series(np.random.normal(0.001, 0.02, 100), index=dates),
            'First Half': pd.Series(np.random.normal(0.001, 0.02, 50), index=dates[:50]),
            'Second Half': pd.Series(np.random.normal(0.001, 0.02, 50), index=dates[50:])
        }
        
        fig = create_time_period_comparison(returns_data)
        if fig:
            print("✅ Time period comparison chart created successfully")
        else:
            print("❌ Time period comparison chart creation failed")
            errors.append("Time period comparison")
    except Exception as e:
        print(f"❌ Time period comparison failed: {e}")
        errors.append(f"Time period comparison: {e}")
    
    print()
    return errors


def test_integration():
    """Test integration with dashboard components."""
    print("=" * 60)
    print("Testing Integration")
    print("=" * 60)
    
    errors = []
    
    # Test that comprehensive analysis page can import enhanced charts
    try:
        from src.app.dashboard.pages.comprehensive_analysis import (
            create_attribution_waterfall,
            create_factor_exposure_heatmap
        )
        print("✅ Comprehensive analysis page imports enhanced charts")
    except ImportError:
        # This is expected - they're imported from components
        print("ℹ️  Enhanced charts imported via components (expected)")
    except Exception as e:
        print(f"⚠️  Comprehensive analysis integration check: {e}")
    
    # Test that app.py can import advanced comparison
    try:
        from src.app.dashboard.app import main
        print("✅ Dashboard app imports successfully")
    except Exception as e:
        print(f"❌ Dashboard app import failed: {e}")
        errors.append(f"Dashboard app: {e}")
    
    # Test config has advanced comparison
    try:
        from src.app.dashboard.config import STANDALONE_TOOLS
        tool_names = [tool[0] for tool in STANDALONE_TOOLS]
        if "🔀 Advanced Comparison" in tool_names:
            print("✅ Advanced Comparison added to navigation")
        else:
            print("❌ Advanced Comparison not in navigation")
            errors.append("Advanced Comparison not in navigation")
    except Exception as e:
        print(f"❌ Config check failed: {e}")
        errors.append(f"Config check: {e}")
    
    print()
    return errors


def main():
    """Run all validation tests."""
    print("\n" + "=" * 60)
    print("Export & Visualization Features Validation")
    print("=" * 60 + "\n")
    
    all_errors = []
    
    # Run tests
    all_errors.extend(test_imports())
    all_errors.extend(test_export_functionality())
    all_errors.extend(test_enhanced_charts())
    all_errors.extend(test_integration())
    
    # Summary
    print("=" * 60)
    print("Validation Summary")
    print("=" * 60)
    
    if all_errors:
        print(f"\n⚠️  Found {len(all_errors)} issue(s):")
        for i, error in enumerate(all_errors, 1):
            print(f"  {i}. {error}")
        print("\n⚠️  Some features may not work correctly.")
        return 1
    else:
        print("\n✅ All tests passed!")
        print("\nFeatures validated:")
        print("  ✅ Export functionality (PDF & Excel)")
        print("  ✅ Enhanced visualizations (waterfall, heatmap, comparison charts)")
        print("  ✅ Advanced comparison tools")
        print("  ✅ GUI integration")
        return 0


if __name__ == '__main__':
    sys.exit(main())
