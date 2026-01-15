"""
Comprehensive Analysis Page
============================
Display all analysis results: attribution, benchmark, factor exposure, AI insights.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from pathlib import Path

from ..components.sidebar import render_page_header
from ..data import load_runs, get_run_folder
from ..utils import format_percent, format_number
from src.analytics.analysis_service import AnalysisService
from src.analytics.data_loader import load_run_data_for_analysis
from src.analytics.comprehensive_analysis import ComprehensiveAnalysisRunner


def render_comprehensive_analysis():
    """Render comprehensive analysis page."""
    render_page_header("📊 Comprehensive Analysis", "Deep dive into portfolio performance")
    
    # Get runs
    runs = load_runs()
    if not runs:
        st.warning("No analysis runs found. Run an analysis first.")
        return
    
    # Run selector
    run_options = {f"{r['name'] or r['run_id'][:16]} ({r['run_id'][:8]})": r['run_id'] 
                   for r in runs}
    selected_run_label = st.selectbox(
        "Select Run",
        options=list(run_options.keys()),
        key="comp_analysis_run"
    )
    selected_run_id = run_options[selected_run_label]
    selected_run = next(r for r in runs if r['run_id'] == selected_run_id)
    
    # Initialize service
    service = AnalysisService()
    
    # Check if analysis exists
    analysis_results = service.get_all_analysis_results(selected_run_id)
    analysis_types = {r.analysis_type for r in analysis_results}
    
    # Run analysis button
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("🔄 Run All Analyses", type="primary", use_container_width=True):
            with st.spinner("Running comprehensive analysis..."):
                try:
                    # Load data
                    run_dir = get_run_folder(selected_run_id, selected_run.get('watchlist'))
                    data = load_run_data_for_analysis(selected_run_id, run_dir)
                    
                    if data['error']:
                        st.error(f"Error loading data: {data['error']}")
                    else:
                        # Run analysis
                        runner = ComprehensiveAnalysisRunner()
                        results = runner.run_all_analysis(
                            run_id=selected_run_id,
                            portfolio_data=data['portfolio_data'] or {},
                            stock_data=data['stock_data'],
                            save_ai_insights=True
                        )
                        st.success("✅ Analysis complete!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error running analysis: {e}")
                    import traceback
                    st.code(traceback.format_exc())
    
    with col2:
        export_format = st.selectbox("Export Format", ["PDF", "Excel"], key="export_format")
        if st.button("📥 Export Results", use_container_width=True):
            try:
                from ..export import export_to_pdf, export_to_excel
                
                # Collect all analysis results
                all_results = {}
                for analysis_type in ['attribution', 'benchmark_comparison', 'factor_exposure', 'rebalancing', 'style']:
                    result = service.get_analysis_result(selected_run_id, analysis_type)
                    if result:
                        all_results[analysis_type] = {
                            'results': result.get_results() if hasattr(result, 'get_results') else result.results_json,
                            'summary': result.get_summary() if hasattr(result, 'get_summary') else result.summary_json
                        }
                
                if export_format == "PDF":
                    pdf_bytes = export_to_pdf(all_results, selected_run)
                    st.download_button(
                        label="📥 Download PDF",
                        data=pdf_bytes,
                        file_name=f"analysis_{selected_run_id[:16]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf"
                    )
                else:
                    excel_bytes = export_to_excel(all_results, selected_run)
                    st.download_button(
                        label="📥 Download Excel",
                        data=excel_bytes,
                        file_name=f"analysis_{selected_run_id[:16]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            except ImportError as e:
                st.error(f"Export requires additional packages: {e}")
            except Exception as e:
                st.error(f"Export failed: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    st.markdown("---")
    
    # Display analysis results
    tabs = st.tabs([
        "📈 Performance Attribution",
        "📊 Benchmark Comparison", 
        "🔍 Factor Exposure",
        "⚖️ Rebalancing",
        "🎨 Style Analysis",
        "🤖 AI Insights",
        "💡 Recommendations"
    ])
    
    # Performance Attribution Tab
    with tabs[0]:
        _render_attribution_tab(service, selected_run_id, analysis_types)
    
    # Benchmark Comparison Tab
    with tabs[1]:
        _render_benchmark_tab(service, selected_run_id, analysis_types)
    
    # Factor Exposure Tab
    with tabs[2]:
        _render_factor_tab(service, selected_run_id, analysis_types)
    
    # Rebalancing Tab
    with tabs[3]:
        _render_rebalancing_tab(service, selected_run_id, analysis_types)
    
    # Style Analysis Tab
    with tabs[4]:
        _render_style_tab(service, selected_run_id, analysis_types)
    
    # AI Insights Tab
    with tabs[5]:
        _render_ai_insights_tab(service, selected_run_id)
    
    # Recommendations Tab
    with tabs[6]:
        _render_recommendations_tab(service, selected_run_id)


def _render_attribution_tab(service: AnalysisService, run_id: str, analysis_types: set):
    """Render performance attribution tab."""
    if 'attribution' not in analysis_types:
        st.info("Performance attribution not yet calculated. Click 'Run All Analyses' to generate.")
        return
    
    result = service.get_analysis_result(run_id, 'attribution')
    if not result:
        st.warning("Attribution data not found.")
        return
    
    attribution = result.get_results()
    
    # Summary metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Return", format_percent(attribution.get('total_return', 0)))
    with col2:
        st.metric("Factor", format_percent(attribution['attributions'].get('factor', 0)))
    with col3:
        st.metric("Sector", format_percent(attribution['attributions'].get('sector', 0)))
    with col4:
        st.metric("Stock Selection", format_percent(attribution['attributions'].get('stock_selection', 0)))
    with col5:
        st.metric("Timing", format_percent(attribution['attributions'].get('timing', 0)))
    
    # Attribution waterfall chart
    st.markdown("### Attribution Waterfall Chart")
    waterfall_data = {
        'factor_attribution': attribution['attributions'].get('factor', 0),
        'sector_attribution': attribution['attributions'].get('sector', 0),
        'stock_selection_attribution': attribution['attributions'].get('stock_selection', 0),
        'timing_attribution': attribution['attributions'].get('timing', 0),
        'total_return': attribution.get('total_return', 0)
    }
    fig = create_attribution_waterfall(waterfall_data, "Performance Attribution Waterfall")
    st.plotly_chart(fig, use_container_width=True)
    
    # Also show bar chart for comparison
    st.markdown("### Attribution Breakdown (Bar Chart)")
    attributions = attribution['attributions']
    fig = go.Figure(data=[
        go.Bar(
            x=list(attributions.keys()),
            y=[attributions.get(k, 0) * 100 for k in attributions.keys()],
            marker_color=['#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b'],
            text=[f"{attributions.get(k, 0)*100:.2f}%" for k in attributions.keys()],
            textposition='outside'
        )
    ])
    fig.update_layout(
        title="Performance Attribution Breakdown",
        xaxis_title="Attribution Component",
        yaxis_title="Return Contribution (%)",
        height=400,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed breakdown
    if 'breakdown' in attribution:
        st.subheader("Detailed Breakdown")
        breakdown = attribution['breakdown']
        
        if 'factor' in breakdown:
            st.write("**Factor Attribution:**")
            factor_df = pd.DataFrame(list(breakdown['factor']['by_factor'].items()), 
                                   columns=['Factor', 'Contribution'])
            st.dataframe(factor_df, use_container_width=True)
        
        if 'sector' in breakdown:
            st.write("**Sector Attribution:**")
            sector_df = pd.DataFrame(list(breakdown['sector']['by_sector'].items()),
                                   columns=['Sector', 'Contribution'])
            st.dataframe(sector_df, use_container_width=True)


def _render_benchmark_tab(service: AnalysisService, run_id: str, analysis_types: set):
    """Render benchmark comparison tab."""
    if 'benchmark_comparison' not in analysis_types:
        st.info("Benchmark comparison not yet calculated. Click 'Run All Analyses' to generate.")
        return
    
    result = service.get_analysis_result(run_id, 'benchmark_comparison')
    if not result:
        st.warning("Benchmark comparison data not found.")
        return
    
    comparisons = result.get_results()
    
    # Display comparisons for each benchmark
    for benchmark_symbol, comparison in comparisons.items():
        if 'error' in comparison:
            st.warning(f"Error comparing to {benchmark_symbol}: {comparison['error']}")
            continue
        
        st.subheader(f"vs {comparison.get('benchmark_name', benchmark_symbol)}")
        
        portfolio_metrics = comparison['portfolio_metrics']
        benchmark_metrics = comparison['benchmark_metrics']
        relative_metrics = comparison['relative_metrics']
        
        # Metrics comparison
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("**Portfolio**")
            st.metric("Return", format_percent(portfolio_metrics.get('return', 0)))
            st.metric("Sharpe", f"{portfolio_metrics.get('sharpe', 0):.2f}")
            st.metric("Max DD", format_percent(portfolio_metrics.get('max_drawdown', 0)))
        
        with col2:
            st.write("**Benchmark**")
            st.metric("Return", format_percent(benchmark_metrics.get('return', 0)))
            st.metric("Sharpe", f"{benchmark_metrics.get('sharpe', 0):.2f}")
            st.metric("Max DD", format_percent(benchmark_metrics.get('max_drawdown', 0)))
        
        with col3:
            st.write("**Relative**")
            alpha = relative_metrics.get('alpha', 0)
            beta = relative_metrics.get('beta', 1)
            st.metric("Alpha", format_percent(alpha), 
                     delta=f"{alpha*100:.2f}%" if alpha else None)
            st.metric("Beta", f"{beta:.2f}")
            st.metric("Info Ratio", f"{relative_metrics.get('information_ratio', 0):.2f}")
        
        st.markdown("---")


def _render_factor_tab(service: AnalysisService, run_id: str, analysis_types: set):
    """Render factor exposure tab."""
    if 'factor_exposure' not in analysis_types:
        st.info("Factor exposure analysis not yet calculated. Click 'Run All Analyses' to generate.")
        return
    
    result = service.get_analysis_result(run_id, 'factor_exposure')
    if not result:
        st.warning("Factor exposure data not found.")
        return
    
    factor_data = result.get_results()
    factor_exposures = factor_data.get('factor_exposures', [])
    
    if not factor_exposures:
        st.info("No factor exposures calculated.")
        return
    
    # Factor exposure heatmap
    st.markdown("### Factor Exposure Heatmap")
    exposures_dict = {}
    for factor in factor_exposures:
        exposures_dict[factor['factor_name']] = {
            'exposure': factor.get('exposure', 0),
            'contribution_to_return': factor.get('contribution_to_return', 0),
            'contribution_to_risk': factor.get('contribution_to_risk', 0)
        }
    
    fig = create_factor_exposure_heatmap(exposures_dict, "Factor Exposure Analysis")
    st.plotly_chart(fig, use_container_width=True)
    
    # Also show bar chart
    st.markdown("### Factor Exposures (Bar Chart)")
    factors_df = pd.DataFrame(factor_exposures)
    fig = go.Figure(data=[
        go.Bar(
            x=factors_df['factor_name'],
            y=factors_df['exposure'],
            marker_color=factors_df['exposure'].apply(
                lambda x: '#10b981' if x > 0 else '#ef4444'
            ),
            text=[f"{x:.3f}" for x in factors_df['exposure']],
            textposition='outside'
        )
    ])
    fig.update_layout(
        title="Factor Exposures",
        xaxis_title="Factor",
        yaxis_title="Exposure",
        height=400,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)
    
    # Factor details table
    st.subheader("Factor Details")
    display_df = factors_df[['factor_name', 'factor_type', 'exposure', 
                             'contribution_to_return', 'contribution_to_risk']].copy()
    display_df.columns = ['Factor', 'Type', 'Exposure', 'Return Contribution', 'Risk Contribution']
    st.dataframe(display_df, use_container_width=True)


def _render_ai_insights_tab(service: AnalysisService, run_id: str):
    """Render AI insights tab."""
    insights = service.get_all_ai_insights(run_id)
    
    if not insights:
        st.info("No AI insights found. Generate insights from the AI Insights page.")
        return
    
    # Group by type
    insight_types = {}
    for insight in insights:
        itype = insight.insight_type
        if itype not in insight_types:
            insight_types[itype] = []
        insight_types[itype].append(insight)
    
    # Display each type
    for insight_type, insight_list in insight_types.items():
        # Get latest
        latest = max(insight_list, key=lambda x: x.created_at)
        
        st.subheader(insight_type.replace('_', ' ').title())
        st.markdown(f"*Generated: {latest.created_at.strftime('%Y-%m-%d %H:%M')}*")
        st.markdown("---")
        st.markdown(latest.content)
        st.markdown("---")


def _render_rebalancing_tab(service: AnalysisService, run_id: str, analysis_types: set):
    """Render rebalancing analysis tab."""
    if 'rebalancing' not in analysis_types:
        st.info("Rebalancing analysis not yet calculated. Click 'Run All Analyses' to generate.")
        return
    
    result = service.get_analysis_result(run_id, 'rebalancing')
    if not result:
        st.warning("Rebalancing data not found.")
        return
    
    rebalancing = result.get_results()
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Current Drift", format_percent(rebalancing.get('current_drift', 0)))
    with col2:
        st.metric("Avg Turnover", format_percent(rebalancing.get('avg_turnover', 0)))
    with col3:
        st.metric("Total Cost", format_percent(rebalancing.get('total_transaction_cost', 0)))
    with col4:
        st.metric("Rebalance Events", rebalancing.get('rebalance_events', 0))
    
    # Recommendation
    recommendation = rebalancing.get('recommendation', '')
    if 'Rebalance now' in recommendation:
        st.warning(recommendation)
    else:
        st.info(recommendation)
    
    # Optimal frequency
    if 'optimal_frequency' in rebalancing:
        opt_freq = rebalancing['optimal_frequency']
        st.subheader("Optimal Rebalancing Frequency")
        st.write(f"**Recommended:** {opt_freq.get('recommended', 'unknown').title()}")
        
        if 'frequencies' in opt_freq:
            freq_df = pd.DataFrame(opt_freq['frequencies']).T
            st.dataframe(freq_df, use_container_width=True)


def _render_style_tab(service: AnalysisService, run_id: str, analysis_types: set):
    """Render style analysis tab."""
    if 'style' not in analysis_types:
        st.info("Style analysis not yet calculated. Click 'Run All Analyses' to generate.")
        return
    
    result = service.get_analysis_result(run_id, 'style')
    if not result:
        st.warning("Style analysis data not found.")
        return
    
    style = result.get_results()
    
    if 'error' in style:
        st.error(f"Error: {style['error']}")
        return
    
    # Overall style
    gv_class = style.get('growth_value', {}).get('classification', 'Unknown')
    size_class = style.get('size', {}).get('classification', 'Unknown')
    overall = f"{gv_class} {size_class}"
    st.metric("Overall Style", overall)
    
    # Growth vs Value
    if 'growth_value' in style and style['growth_value']:
        gv = style['growth_value']
        st.subheader("Growth vs Value")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Classification:** {gv.get('classification', 'unknown').title()}")
        with col2:
            if 'portfolio_pe' in gv:
                st.write(f"**Portfolio PE:** {gv['portfolio_pe']:.2f}")
                if 'weighted_avg_pe' in gv:
                    st.write(f"**Weighted Avg PE:** {gv['weighted_avg_pe']:.2f}")
    
    # Size
    if 'size' in style and style['size']:
        size = style['size']
        st.subheader("Size Classification")
        st.write(f"**Classification:** {size.get('classification', 'unknown')}")
        if 'portfolio_market_cap_billions' in size:
            st.write(f"**Portfolio Market Cap:** ${size['portfolio_market_cap_billions']:.2f}B")


def _render_recommendations_tab(service: AnalysisService, run_id: str):
    """Render recommendations tab."""
    recommendations = service.get_recommendations(run_id=run_id)
    
    if not recommendations:
        st.info("No recommendations found for this run.")
        return
    
    # Group by action
    by_action = {}
    for rec in recommendations:
        action = rec.action
        if action not in by_action:
            by_action[action] = []
        by_action[action].append(rec)
    
    for action, recs in by_action.items():
        st.subheader(f"{action} Recommendations ({len(recs)})")
        
        recs_df = pd.DataFrame([{
            'Ticker': r.ticker,
            'Date': r.recommendation_date.strftime('%Y-%m-%d') if r.recommendation_date else '',
            'Reason': r.reason or '',
            'Confidence': f"{r.confidence*100:.0f}%" if r.confidence else '',
            'Target': f"${r.target_price:.2f}" if r.target_price else '',
            'Return': format_percent(r.actual_return) if r.actual_return else ''
        } for r in recs])
        
        st.dataframe(recs_df, use_container_width=True)
        st.markdown("---")
